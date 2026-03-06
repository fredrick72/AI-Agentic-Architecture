"""
Query Orchestrator - Text-to-SQL reasoning loop

Flow for each user question:
  1. Retrieve relevant table schemas via RAG (schema service)
  2. Build SQL generation prompt with schema context
  3. Call LLM to generate SQL (GPT-4o)
  4. Run guardrail checks on the generated SQL
  5. If blocked: return guardrail error (do NOT execute)
  6. If safe: execute against target DB
  7. Call LLM to explain results in plain language (GPT-4o-mini)
  8. Log to audit table
  9. Return structured response

The orchestrator never receives the raw connection string at query time —
it looks it up from the app's own DB by connection_id, so users cannot
inject alternate credentials.
"""
import json
import logging
import uuid
from datetime import datetime
from typing import Any

import httpx
import psycopg2
import psycopg2.extras

from config import settings
from guardrails import SQLGuardrails
from db_executor import DBExecutor
from llm_client import LLMClient

logger = logging.getLogger(__name__)


SQL_SYSTEM_PROMPT = """\
You are an expert SQL analyst. Your job is to write a single, correct \
SELECT query to answer the user's question.

Rules you must follow:
- Write ONLY the SQL query. No explanation, no markdown fences, no commentary.
- Only SELECT statements. Never INSERT, UPDATE, DELETE, DROP, or any DDL.
- Use explicit column names — never SELECT *.
- Always include a LIMIT clause (default: 100 rows unless the user asks for more).
- Use table aliases for clarity when joining multiple tables.
- Prefer INNER JOIN unless the question implies optional relationships.
- Quote identifiers that might be reserved words or contain spaces.
- If the question is ambiguous, choose the most reasonable interpretation.
- If you cannot answer with the available tables, output exactly: CANNOT_ANSWER

Available schema (retrieved for this specific question):
{schema_context}
"""

EXPLAIN_SYSTEM_PROMPT = """\
You are a helpful data analyst explaining query results to a non-technical user.
Be concise (2-4 sentences). Highlight the most important finding.
If the result set is empty, say so clearly and suggest why that might be.
Do not describe column names — describe the data and what it means.
"""


class QueryOrchestrator:
    def __init__(self):
        self.guardrails = SQLGuardrails(
            max_rows=settings.max_result_rows,
            max_query_length=8000,
        )
        self.executor = DBExecutor(
            timeout_seconds=settings.query_timeout_seconds,
            max_rows=settings.max_result_rows,
        )
        self.llm = LLMClient(settings.openai_api_key)

    def run(
        self,
        connection_id: str,
        question: str,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Process a natural-language question against a registered connection.

        Returns:
            {
                "answer": str,           # plain-language explanation
                "sql": str | None,       # generated SQL (shown in UI)
                "columns": [...],        # column names
                "rows": [[...]],         # result rows
                "row_count": int,
                "truncated": bool,
                "execution_time_ms": int,
                "guardrail_blocked": bool,
                "guardrail_reason": str | None,
                "tokens_used": int,
                "cost_usd": float,
                "audit_id": str,
            }
        """
        audit_id = str(uuid.uuid4())
        session_id = session_id or str(uuid.uuid4())
        total_tokens = 0
        total_cost = 0.0

        try:
            # --- 1. Look up connection ---
            connection_string = self._get_connection_string(connection_id)

            # --- 2. Retrieve relevant schema via RAG ---
            schema_results = self._retrieve_schema(connection_id, question)
            schema_context = self._format_schema_context(schema_results)

            # --- 3. Generate SQL ---
            sql_response = self.llm.generate_sql(
                system_prompt=SQL_SYSTEM_PROMPT.format(schema_context=schema_context),
                user_message=question,
            )
            total_tokens += sql_response["input_tokens"] + sql_response["output_tokens"]
            total_cost += sql_response["cost_usd"]

            raw_sql = sql_response["response"].strip()

            # Handle CANNOT_ANSWER signal
            if raw_sql.upper().startswith("CANNOT_ANSWER"):
                self._log_audit(
                    audit_id=audit_id,
                    connection_id=connection_id,
                    session_id=session_id,
                    question=question,
                    generated_sql=None,
                    guardrail_blocked=False,
                    execution_status="cannot_answer",
                    tokens=total_tokens,
                    cost=total_cost,
                )
                return {
                    "answer": (
                        "I couldn't find tables in your schema that would answer this question. "
                        "Try rephrasing, or check that the relevant data exists."
                    ),
                    "sql": None,
                    "columns": [],
                    "rows": [],
                    "row_count": 0,
                    "truncated": False,
                    "execution_time_ms": 0,
                    "guardrail_blocked": False,
                    "guardrail_reason": None,
                    "tokens_used": total_tokens,
                    "cost_usd": round(total_cost, 6),
                    "audit_id": audit_id,
                }

            # Clean up any accidental markdown code fences from the LLM
            raw_sql = self._strip_code_fences(raw_sql)

            # --- 4. Guardrail validation ---
            safe, reason = self.guardrails.validate(raw_sql)
            if not safe:
                logger.warning(f"Guardrail blocked query: {reason}\nSQL: {raw_sql}")
                self._log_audit(
                    audit_id=audit_id,
                    connection_id=connection_id,
                    session_id=session_id,
                    question=question,
                    generated_sql=raw_sql,
                    guardrail_blocked=True,
                    guardrail_reason=reason,
                    execution_status="blocked",
                    tokens=total_tokens,
                    cost=total_cost,
                )
                return {
                    "answer": f"The generated query was blocked by safety guardrails: {reason}",
                    "sql": raw_sql,
                    "columns": [],
                    "rows": [],
                    "row_count": 0,
                    "truncated": False,
                    "execution_time_ms": 0,
                    "guardrail_blocked": True,
                    "guardrail_reason": reason,
                    "tokens_used": total_tokens,
                    "cost_usd": round(total_cost, 6),
                    "audit_id": audit_id,
                }

            # --- 5. Add LIMIT if missing ---
            bounded_sql = self.guardrails.add_limit(raw_sql)

            # --- 6. Execute ---
            exec_result = self.executor.execute(connection_string, bounded_sql)

            # --- 7. Explain results ---
            explanation_input = self._format_for_explanation(
                question, bounded_sql, exec_result
            )
            explain_response = self.llm.explain_results(
                system_prompt=EXPLAIN_SYSTEM_PROMPT,
                user_message=explanation_input,
            )
            total_tokens += explain_response["input_tokens"] + explain_response["output_tokens"]
            total_cost += explain_response["cost_usd"]

            # --- 8. Audit log ---
            self._log_audit(
                audit_id=audit_id,
                connection_id=connection_id,
                session_id=session_id,
                question=question,
                generated_sql=bounded_sql,
                guardrail_blocked=False,
                execution_status="success",
                row_count=exec_result["row_count"],
                execution_time_ms=exec_result["execution_time_ms"],
                tokens=total_tokens,
                cost=total_cost,
                result_sample=exec_result["rows"][:5],
                explanation=explain_response["response"],
            )

            return {
                "answer": explain_response["response"],
                "sql": bounded_sql,
                "columns": exec_result["columns"],
                "rows": exec_result["rows"],
                "row_count": exec_result["row_count"],
                "truncated": exec_result["truncated"],
                "execution_time_ms": exec_result["execution_time_ms"],
                "guardrail_blocked": False,
                "guardrail_reason": None,
                "tokens_used": total_tokens,
                "cost_usd": round(total_cost, 6),
                "audit_id": audit_id,
            }

        except Exception as e:
            logger.error(f"Orchestration error: {e}", exc_info=True)
            self._log_audit(
                audit_id=audit_id,
                connection_id=connection_id,
                session_id=session_id,
                question=question,
                generated_sql=None,
                guardrail_blocked=False,
                execution_status="error",
                tokens=total_tokens,
                cost=total_cost,
            )
            raise

    # ------------------------------------------------------------------ #
    #  Internal helpers                                                    #
    # ------------------------------------------------------------------ #

    def _get_connection_string(self, connection_id: str) -> str:
        conn = psycopg2.connect(settings.postgres_url)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT connection_string, status FROM connections WHERE id = %s",
                    (connection_id,)
                )
                row = cur.fetchone()
                if not row:
                    raise ValueError(f"Connection not found: {connection_id}")
                cs, status = row
                if status != "ready":
                    raise ValueError(
                        f"Connection '{connection_id}' is not ready (status: {status}). "
                        "Wait for the schema crawl to complete."
                    )
                return cs
        finally:
            conn.close()

    def _retrieve_schema(
        self, connection_id: str, question: str, top_k: int = 6
    ) -> list[dict[str, Any]]:
        """Call the schema service to get relevant table chunks."""
        try:
            with httpx.Client(timeout=15) as client:
                resp = client.post(
                    f"{settings.schema_service_url}/connections/{connection_id}/search",
                    json={"query": question, "top_k": top_k},
                )
                resp.raise_for_status()
                return resp.json().get("results", [])
        except Exception as e:
            logger.warning(f"Schema retrieval failed: {e}")
            return []

    def _format_schema_context(self, schema_results: list[dict[str, Any]]) -> str:
        """Format retrieved schema chunks into a prompt block."""
        if not schema_results:
            return "(No relevant schema found — answer CANNOT_ANSWER)"

        blocks = []
        for r in schema_results:
            similarity = r.get("similarity", 0)
            # Parse the raw_schema JSON if available for the structured schema_block
            raw = r.get("raw_schema")
            if raw:
                try:
                    table_info = json.loads(raw) if isinstance(raw, str) else raw
                    block = table_info.get("schema_block") or r.get("content", "")
                except Exception:
                    block = r.get("content", "")
            else:
                block = r.get("content", "")
            blocks.append(block)

        return "\n\n".join(blocks)

    def _format_for_explanation(
        self,
        question: str,
        sql: str,
        exec_result: dict[str, Any],
    ) -> str:
        """Build the explanation prompt content."""
        row_count = exec_result["row_count"]
        truncated = exec_result.get("truncated", False)
        columns = exec_result["columns"]
        sample_rows = exec_result["rows"][:5]

        sample_text = ""
        if sample_rows:
            header = " | ".join(columns)
            rows_text = "\n".join(
                " | ".join(str(cell) for cell in row) for row in sample_rows
            )
            sample_text = f"\nSample results (first {len(sample_rows)} of {row_count}):\n{header}\n{rows_text}"

        truncation_note = f"\n(Results were capped at {row_count} rows)" if truncated else ""

        return (
            f"User question: {question}\n"
            f"SQL executed:\n{sql}\n"
            f"Returned {row_count} rows.{truncation_note}"
            f"{sample_text}"
        )

    def _strip_code_fences(self, sql: str) -> str:
        """Remove ```sql ... ``` or ``` ... ``` fences that GPT sometimes adds."""
        import re
        sql = re.sub(r"^```(?:sql)?\s*", "", sql.strip(), flags=re.IGNORECASE)
        sql = re.sub(r"\s*```$", "", sql.strip())
        return sql.strip()

    def _log_audit(
        self,
        audit_id: str,
        connection_id: str,
        session_id: str,
        question: str,
        generated_sql: str | None,
        guardrail_blocked: bool,
        execution_status: str,
        guardrail_reason: str | None = None,
        row_count: int | None = None,
        execution_time_ms: int | None = None,
        tokens: int = 0,
        cost: float = 0.0,
        result_sample: list | None = None,
        explanation: str | None = None,
    ):
        try:
            conn = psycopg2.connect(settings.postgres_url)
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO query_audit (
                        id, connection_id, session_id, user_question,
                        generated_sql, guardrail_blocked, guardrail_reason,
                        execution_status, row_count, execution_time_ms,
                        llm_tokens_used, llm_cost_usd,
                        result_sample, agent_explanation
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (
                        audit_id, connection_id, session_id, question,
                        generated_sql, guardrail_blocked, guardrail_reason,
                        execution_status, row_count, execution_time_ms,
                        tokens, cost,
                        json.dumps(result_sample) if result_sample else None,
                        explanation,
                    )
                )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"Audit log failed: {e}")
