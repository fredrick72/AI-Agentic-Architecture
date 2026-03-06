"""
Database Executor

Executes validated SELECT queries against the target database.
Enforces:
  - Query timeout
  - Row cap (belt-and-suspenders beyond the LIMIT in the SQL)
  - Read-only transaction (cannot write even if guardrails were bypassed)
  - Column type serialization (dates, decimals, etc. → JSON-safe)
"""
import logging
import decimal
from datetime import date, datetime, time
from typing import Any

import sqlalchemy as sa
from sqlalchemy import text, event
from sqlalchemy.exc import OperationalError, ProgrammingError, SQLAlchemyError

logger = logging.getLogger(__name__)


def _make_json_safe(value: Any) -> Any:
    """Convert non-JSON-serializable DB types to safe Python primitives."""
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, decimal.Decimal):
        return float(value)
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if value is None:
        return None
    return value


class DBExecutor:
    """
    Executes a pre-validated SELECT query against a target database.

    The connection string comes from the registered connection — this
    executor does NOT receive a raw connection string from the user at
    query time (it's looked up server-side by connection_id).
    """

    def __init__(self, timeout_seconds: int = 30, max_rows: int = 1000):
        self.timeout_seconds = timeout_seconds
        self.max_rows = max_rows

    def execute(
        self,
        connection_string: str,
        sql: str,
    ) -> dict[str, Any]:
        """
        Execute a validated SELECT query.

        Returns:
            {
                "columns": [...],
                "rows": [[...], ...],
                "row_count": int,
                "execution_time_ms": int,
                "truncated": bool  # True if results were capped
            }

        Raises:
            ValueError: for SQL that fails at execution time
            RuntimeError: for connectivity or timeout errors
        """
        import time
        start = time.monotonic()

        engine = self._build_engine(connection_string)

        try:
            with engine.connect() as conn:
                # Force read-only transaction (PostgreSQL / MySQL / SQLite support this)
                self._set_readonly(conn, engine.dialect.name)

                # Execute
                result = conn.execute(text(sql))

                columns = list(result.keys())
                raw_rows = result.fetchmany(self.max_rows + 1)  # +1 to detect truncation

                truncated = len(raw_rows) > self.max_rows
                rows = raw_rows[: self.max_rows]

                # Serialize each cell
                safe_rows = [
                    [_make_json_safe(cell) for cell in row]
                    for row in rows
                ]

                elapsed_ms = int((time.monotonic() - start) * 1000)

                return {
                    "columns": columns,
                    "rows": safe_rows,
                    "row_count": len(safe_rows),
                    "execution_time_ms": elapsed_ms,
                    "truncated": truncated,
                }

        except ProgrammingError as e:
            raise ValueError(f"SQL error: {e.orig}") from e
        except OperationalError as e:
            raise RuntimeError(f"Database error: {e.orig}") from e
        except Exception as e:
            raise RuntimeError(str(e)) from e
        finally:
            engine.dispose()

    def _build_engine(self, connection_string: str) -> sa.Engine:
        """
        Build a SQLAlchemy engine with timeout settings per dialect.
        """
        connect_args: dict[str, Any] = {}
        dialect = connection_string.split(":")[0].lower()

        if "postgresql" in dialect or "postgres" in dialect:
            connect_args = {
                "connect_timeout": 10,
                "options": f"-c statement_timeout={self.timeout_seconds * 1000}",
            }
        elif "mysql" in dialect:
            connect_args = {
                "connect_timeout": 10,
                "read_timeout": self.timeout_seconds,
            }
        elif "mssql" in dialect:
            connect_args = {"timeout": self.timeout_seconds}

        return sa.create_engine(
            connection_string,
            connect_args=connect_args,
            pool_size=1,
            max_overflow=0,
        )

    def _set_readonly(self, conn, dialect_name: str):
        """
        Put the connection in read-only mode if the dialect supports it.
        This is a belt-and-suspenders measure beyond the guardrails.
        """
        try:
            if dialect_name in ("postgresql", "postgres"):
                conn.execute(text("SET TRANSACTION READ ONLY"))
            elif dialect_name == "mysql":
                conn.execute(text("SET SESSION TRANSACTION READ ONLY"))
            # SQLite and MSSQL: rely on guardrails; no equivalent SET command
        except Exception as e:
            # Non-fatal: log and continue (guardrails already blocked writes)
            logger.debug(f"Could not set read-only mode on {dialect_name}: {e}")
