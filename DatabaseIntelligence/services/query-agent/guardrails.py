"""
SQL Guardrails

Validates LLM-generated SQL before it touches the database.
All checks are fast, purely structural — no DB round-trip required.

Validation pipeline:
  1. Length sanity check
  2. sqlparse: must parse as a single SELECT statement
  3. Blocked keyword scan (write / DDL / admin operations)
  4. Semicolon injection guard
  5. Comment stripping + re-validation (defends against -- comment tricks)

After validation, add_limit() ensures a LIMIT clause is present and
within the configured maximum.
"""
import logging
import re

import sqlparse
from sqlparse.sql import Statement

logger = logging.getLogger(__name__)

# Any of these words appearing as SQL tokens means the query is not read-only
BLOCKED_KEYWORDS: set[str] = {
    "INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER", "TRUNCATE",
    "GRANT", "REVOKE", "RENAME", "COMMENT",
    # Stored procedure / function execution
    "EXEC", "EXECUTE", "CALL", "DO",
    # Data manipulation shortcuts
    "MERGE", "REPLACE", "UPSERT",
    # Postgres specifics
    "COPY",
    # INTO by itself is fine in SELECT INTO but we block it to be safe
    # "INTO",   # uncomment if needed
}

# Patterns that should never appear even inside comments that slip through
DANGEROUS_PATTERNS: list[re.Pattern] = [
    re.compile(r";\s*(?:DROP|DELETE|UPDATE|INSERT|CREATE|ALTER|TRUNCATE)", re.IGNORECASE),
    re.compile(r"xp_cmdshell", re.IGNORECASE),       # SQL Server command exec
    re.compile(r"OPENROWSET\s*\(", re.IGNORECASE),   # SQL Server external data
    re.compile(r"LOAD_FILE\s*\(", re.IGNORECASE),    # MySQL file read
]


class GuardrailViolation(Exception):
    """Raised when a query fails a guardrail check."""


class SQLGuardrails:
    """
    Validates SQL for read-only safety.

    Usage:
        g = SQLGuardrails(max_rows=500)
        safe, reason = g.validate(sql)
        if safe:
            bounded_sql = g.add_limit(sql)
    """

    def __init__(self, max_rows: int = 1000, max_query_length: int = 8000):
        self.max_rows = max_rows
        self.max_query_length = max_query_length

    def validate(self, sql: str) -> tuple[bool, str]:
        """
        Run all guardrail checks.
        Returns (is_safe, reason_if_not_safe).
        """
        sql = sql.strip()

        # 1. Length check
        if len(sql) > self.max_query_length:
            return False, f"Query too long ({len(sql):,} chars, max {self.max_query_length:,})"

        # 2. Dangerous pattern scan (catches semicolon injection etc.)
        for pattern in DANGEROUS_PATTERNS:
            if pattern.search(sql):
                return False, f"Dangerous pattern detected: {pattern.pattern}"

        # 3. Strip SQL comments before keyword scan
        #    (prevents tricks like: SELECT 1 -- ; DROP TABLE users)
        clean_sql = self._strip_comments(sql)

        # 4. Must parse as exactly one statement
        parsed = sqlparse.parse(clean_sql)
        if not parsed:
            return False, "Could not parse SQL"
        if len(parsed) > 1:
            return False, "Multiple SQL statements are not allowed"

        stmt: Statement = parsed[0]

        # 5. Statement type must be SELECT
        stmt_type = stmt.get_type()
        if stmt_type != "SELECT":
            detected = stmt_type or "unknown"
            return False, f"Only SELECT queries are allowed (detected: {detected})"

        # 6. Blocked keyword scan on the cleaned SQL
        sql_upper = clean_sql.upper()
        for keyword in BLOCKED_KEYWORDS:
            # \b word-boundary avoids false positives (e.g. "TRUNCATED" contains "TRUNCATE")
            if re.search(rf"\b{re.escape(keyword)}\b", sql_upper):
                return False, f"Blocked keyword: {keyword}"

        return True, ""

    def add_limit(self, sql: str) -> str:
        """
        Ensure the query has a LIMIT clause no larger than max_rows.
        If no LIMIT exists, appends one.
        If an existing LIMIT exceeds max_rows, replaces it.
        """
        sql = sql.rstrip(";").strip()
        sql_upper = sql.upper()

        limit_match = re.search(r"\bLIMIT\s+(\d+)\b", sql_upper)
        if limit_match:
            existing = int(limit_match.group(1))
            if existing > self.max_rows:
                # Replace the existing LIMIT value
                sql = re.sub(
                    r"\bLIMIT\s+\d+\b",
                    f"LIMIT {self.max_rows}",
                    sql,
                    flags=re.IGNORECASE,
                    count=1,
                )
        else:
            sql = f"{sql}\nLIMIT {self.max_rows}"

        return sql

    def explain_check(self, sql: str) -> str:
        """
        Wrap in EXPLAIN (no execution) to verify query plan exists.
        Returns the EXPLAIN SQL — caller must execute it.
        """
        return f"EXPLAIN {sql}"

    # ------------------------------------------------------------------ #
    #  Internal helpers                                                    #
    # ------------------------------------------------------------------ #

    def _strip_comments(self, sql: str) -> str:
        """
        Remove SQL line comments (--) and block comments (/* */).
        Uses a simple state-machine approach to avoid regex edge cases.
        """
        result = []
        i = 0
        n = len(sql)
        while i < n:
            # Block comment
            if sql[i] == "/" and i + 1 < n and sql[i + 1] == "*":
                # Find end of block comment
                end = sql.find("*/", i + 2)
                if end == -1:
                    break  # Unterminated comment — discard rest
                i = end + 2
            # Line comment
            elif sql[i] == "-" and i + 1 < n and sql[i + 1] == "-":
                end = sql.find("\n", i + 2)
                if end == -1:
                    break
                i = end + 1
            else:
                result.append(sql[i])
                i += 1
        return "".join(result).strip()
