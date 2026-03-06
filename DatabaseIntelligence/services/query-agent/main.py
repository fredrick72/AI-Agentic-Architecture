"""
Query Agent Service

Endpoints:
  POST /query          - Run a natural-language question against a connection
  GET  /audit          - Query audit log
  GET  /health
"""
import logging
from datetime import datetime
from typing import Any, Optional

import psycopg2
import psycopg2.extras
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from config import settings
from orchestrator import QueryOrchestrator

logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Query Agent",
    description="Text-to-SQL agent with safety guardrails",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

orchestrator = QueryOrchestrator()


# ------------------------------------------------------------------ #
#  Request / Response models                                           #
# ------------------------------------------------------------------ #

class QueryRequest(BaseModel):
    connection_id: str = Field(..., description="Registered connection ID")
    question: str = Field(..., description="Natural language question")
    session_id: Optional[str] = Field(None, description="Optional session ID for grouping queries")


class QueryResponse(BaseModel):
    answer: str
    sql: Optional[str]
    columns: list[str]
    rows: list[list[Any]]
    row_count: int
    truncated: bool
    execution_time_ms: int
    guardrail_blocked: bool
    guardrail_reason: Optional[str]
    tokens_used: int
    cost_usd: float
    audit_id: str


# ------------------------------------------------------------------ #
#  Endpoints                                                           #
# ------------------------------------------------------------------ #

@app.get("/")
async def root():
    return {
        "service": "Query Agent",
        "version": "1.0.0",
        "status": "operational",
    }


@app.get("/health")
async def health():
    try:
        conn = psycopg2.connect(settings.postgres_url)
        conn.close()
        db_ok = True
    except Exception:
        db_ok = False
    return {
        "status": "healthy" if db_ok else "degraded",
        "database": "connected" if db_ok else "disconnected",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.post("/query", response_model=QueryResponse)
async def run_query(request: QueryRequest):
    """
    Translate a natural-language question to SQL, execute it safely,
    and return results with a plain-language explanation.
    """
    if not request.question.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Question cannot be empty"
        )

    try:
        result = orchestrator.run(
            connection_id=request.connection_id,
            question=request.question,
            session_id=request.session_id,
        )
        return QueryResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Query failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query processing failed: {str(e)}"
        )


@app.get("/audit")
async def get_audit_log(
    connection_id: Optional[str] = None,
    session_id: Optional[str] = None,
    limit: int = 50,
):
    """Return recent audit log entries."""
    conn = psycopg2.connect(settings.postgres_url)
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            conditions = []
            params: list[Any] = []

            if connection_id:
                conditions.append("connection_id = %s")
                params.append(connection_id)
            if session_id:
                conditions.append("session_id = %s")
                params.append(session_id)

            where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
            params.append(min(limit, 200))

            cur.execute(
                f"""SELECT id, connection_id, session_id, user_question,
                           generated_sql, guardrail_blocked, guardrail_reason,
                           execution_status, row_count, execution_time_ms,
                           llm_tokens_used, llm_cost_usd, agent_explanation,
                           created_at
                    FROM query_audit
                    {where}
                    ORDER BY created_at DESC
                    LIMIT %s""",
                params
            )
            rows = [dict(r) for r in cur.fetchall()]
            return {"entries": rows, "count": len(rows)}
    finally:
        conn.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8011, log_level=settings.log_level.lower())
