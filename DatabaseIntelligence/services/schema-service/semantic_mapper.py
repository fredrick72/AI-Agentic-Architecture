"""
Semantic Mapper

Takes the raw schema map from the crawler and uses the LLM to produce
human-readable descriptions for each table.  These descriptions are
what gets embedded for RAG retrieval — they are written in domain
language, not schema language.

Also produces a concise "table overview" string used as the prompt
context chunk when we do retrieve a table for SQL generation.
"""
import json
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

DESCRIBE_TABLE_PROMPT = """\
You are a database documentation expert. Given the schema details for a \
single database table, write a concise 2-3 sentence description that:
1. Explains what real-world entity or concept this table represents
2. Mentions the most important columns and what they track
3. Notes any significant relationships to other tables

Be specific and business-focused, not technical. Avoid jargon like \
"stores records of" — instead say what the data IS.

Table schema:
{schema_text}

Description (2-3 sentences only):"""


class SemanticMapper:
    """
    Enriches raw schema with LLM-generated descriptions.

    Each table gets:
      - A natural-language description (for embedding / RAG)
      - A formatted schema block (for SQL generation prompts)
    """

    def __init__(self, openai_api_key: str, model: str = "gpt-4o-mini"):
        self.api_key = openai_api_key
        self.model = model

    def enrich(self, schema_map: dict[str, Any]) -> dict[str, Any]:
        """
        Add semantic descriptions to every table in the schema map.
        Returns the schema_map with each table having a 'description' key added.
        """
        tables = schema_map.get("tables", {})
        relationships = schema_map.get("relationships", [])

        # Build a lookup of which tables each table relates to
        relation_lookup: dict[str, list[str]] = {}
        for rel in relationships:
            relation_lookup.setdefault(rel["from_table"], []).append(rel["to_table"])
            relation_lookup.setdefault(rel["to_table"], []).append(rel["from_table"])

        enriched_tables = {}
        for table_name, table_info in tables.items():
            if table_info.get("error"):
                table_info["description"] = f"Table {table_name} (crawl error: {table_info['error']})"
                table_info["schema_block"] = f"Table: {table_name} [unavailable]"
                enriched_tables[table_name] = table_info
                continue

            schema_text = self._format_schema_for_prompt(
                table_info, relation_lookup.get(table_name, [])
            )

            description = self._generate_description(table_name, schema_text)
            table_info["description"] = description
            table_info["schema_block"] = self._format_schema_block(table_info)
            enriched_tables[table_name] = table_info

        schema_map["tables"] = enriched_tables
        return schema_map

    def _format_schema_for_prompt(
        self, table_info: dict[str, Any], related_tables: list[str]
    ) -> str:
        """Build a compact schema description for the LLM describe prompt."""
        lines = [f"Table: {table_info['name']}"]

        if table_info.get("comment"):
            lines.append(f"Comment: {table_info['comment']}")

        lines.append(f"Row count: ~{table_info.get('row_count', 'unknown'):,}")

        if table_info.get("primary_key"):
            lines.append(f"Primary key: {', '.join(table_info['primary_key'])}")

        lines.append("Columns:")
        for col in table_info.get("columns", []):
            col_line = f"  - {col['name']} ({col['type']})"
            if not col.get("nullable"):
                col_line += " NOT NULL"
            if col.get("comment"):
                col_line += f" -- {col['comment']}"
            if col.get("sample_values"):
                samples = col["sample_values"][:8]
                col_line += f"  [sample values: {', '.join(samples)}]"
            lines.append(col_line)

        if table_info.get("foreign_keys"):
            lines.append("Foreign keys:")
            for fk in table_info["foreign_keys"]:
                from_cols = ", ".join(fk["constrained_columns"])
                to_cols = ", ".join(fk["referred_columns"])
                lines.append(f"  - {from_cols} -> {fk['referred_table']}.{to_cols}")

        if related_tables:
            lines.append(f"Related tables: {', '.join(set(related_tables))}")

        return "\n".join(lines)

    def _format_schema_block(self, table_info: dict[str, Any]) -> str:
        """
        Format the table schema as a compact block for SQL generation prompts.
        This is what gets injected into the Text-to-SQL prompt alongside retrieved tables.
        """
        lines = [f"[Table: {table_info['name']}]"]

        if table_info.get("row_count", -1) >= 0:
            lines.append(f"  Rows: ~{table_info['row_count']:,}")

        if table_info.get("description"):
            lines.append(f"  Purpose: {table_info['description']}")

        lines.append("  Columns:")
        pk_set = set(table_info.get("primary_key", []))
        for col in table_info.get("columns", []):
            flags = []
            if col["name"] in pk_set:
                flags.append("PK")
            if not col.get("nullable"):
                flags.append("NOT NULL")
            flag_str = f" [{', '.join(flags)}]" if flags else ""
            sample_str = ""
            if col.get("sample_values"):
                samples = col["sample_values"][:6]
                sample_str = f"  values: {', '.join(repr(s) for s in samples)}"
            lines.append(f"    {col['name']}: {col['type']}{flag_str}{sample_str}")

        if table_info.get("foreign_keys"):
            lines.append("  Foreign keys:")
            for fk in table_info["foreign_keys"]:
                from_cols = ", ".join(fk["constrained_columns"])
                to_cols = ", ".join(fk["referred_columns"])
                lines.append(f"    {from_cols} -> {fk['referred_table']}.{to_cols}")

        return "\n".join(lines)

    def _generate_description(self, table_name: str, schema_text: str) -> str:
        """Call OpenAI to generate a natural-language table description."""
        prompt = DESCRIBE_TABLE_PROMPT.format(schema_text=schema_text)
        try:
            with httpx.Client(timeout=30) as client:
                resp = client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 200,
                        "temperature": 0.2,
                    },
                )
                resp.raise_for_status()
                return resp.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.warning(f"LLM description failed for {table_name}: {e}")
            # Fallback: build a mechanical description from schema
            col_names = [c["name"] for c in []]  # will be empty but won't crash
            return f"Table {table_name} containing database records."
