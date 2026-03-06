"""
Database Schema Crawler

Introspects a target database schema and builds a rich semantic map.
For each table, extracts:
  - Column names, types, nullability, defaults, comments
  - Primary keys and foreign keys
  - Indexes
  - Sample distinct values for low-cardinality / code columns
  - Row count estimate
  - Table-level comments (if supported by the DB)

Supports: PostgreSQL, MySQL, SQLite, Microsoft SQL Server
(via SQLAlchemy's dialect-agnostic reflection API)
"""
import logging
from typing import Any

import sqlalchemy as sa
from sqlalchemy import inspect, text
from sqlalchemy.exc import OperationalError, SQLAlchemyError

logger = logging.getLogger(__name__)

# Columns with these type prefixes are candidates for sample value collection
CATEGORICAL_TYPE_PREFIXES = ("VARCHAR", "CHAR", "TEXT", "ENUM", "NVARCHAR", "NCHAR")

# Skip sampling if cardinality is too high (numeric/blob columns etc.)
NUMERIC_TYPE_PREFIXES = ("INT", "BIGINT", "SMALLINT", "FLOAT", "DOUBLE", "DECIMAL", "NUMERIC", "REAL")


class SchemaCrawler:
    """
    Connects to a target database and introspects its schema.

    Usage:
        crawler = SchemaCrawler("postgresql://user:pass@host/db")
        schema = crawler.crawl()
    """

    def __init__(self, connection_string: str, sample_values_limit: int = 20):
        self.connection_string = connection_string
        self.sample_values_limit = sample_values_limit
        self._engine: sa.Engine | None = None

    def _get_engine(self) -> sa.Engine:
        if self._engine is None:
            dialect = self.connection_string.split(":")[0].lower()
            if "mssql" in dialect:
                connect_args: dict = {"timeout": 10}
            elif "mysql" in dialect:
                connect_args = {"connect_timeout": 10}
            elif "sqlite" in dialect:
                connect_args = {}
            else:  # postgresql
                connect_args = {"connect_timeout": 10}
            self._engine = sa.create_engine(
                self.connection_string,
                connect_args=connect_args,
                pool_pre_ping=True,
            )
        return self._engine

    def test_connection(self) -> tuple[bool, str]:
        """Verify the connection string works before a full crawl."""
        try:
            engine = self._get_engine()
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True, ""
        except OperationalError as e:
            return False, f"Connection failed: {e.orig}"
        except Exception as e:
            return False, str(e)

    def crawl(self) -> dict[str, Any]:
        """
        Full schema crawl. Returns a complete schema map.

        Returns:
            {
                "tables": { table_name: TableInfo },
                "relationships": [ RelationshipInfo ],
                "summary": { table_count, total_rows_estimate, db_type }
            }
        """
        engine = self._get_engine()
        inspector = inspect(engine)

        db_type = engine.dialect.name
        logger.info(f"Crawling {db_type} database schema...")

        schema_map: dict[str, Any] = {
            "tables": {},
            "relationships": [],
            "summary": {}
        }

        table_names = inspector.get_table_names()
        logger.info(f"Found {len(table_names)} tables")

        for table_name in table_names:
            try:
                schema_map["tables"][table_name] = self._crawl_table(
                    inspector, engine, table_name, db_type
                )
            except Exception as e:
                logger.warning(f"Failed to crawl table {table_name}: {e}")
                schema_map["tables"][table_name] = {
                    "name": table_name,
                    "error": str(e),
                    "columns": [],
                    "primary_key": [],
                    "foreign_keys": [],
                    "indexes": [],
                    "row_count": -1,
                    "comment": ""
                }

        schema_map["relationships"] = self._extract_relationships(schema_map["tables"])
        schema_map["summary"] = self._build_summary(schema_map["tables"], db_type)

        logger.info(
            f"Crawl complete: {len(schema_map['tables'])} tables, "
            f"{len(schema_map['relationships'])} relationships"
        )

        return schema_map

    def _crawl_table(
        self,
        inspector: sa.engine.Inspector,
        engine: sa.Engine,
        table_name: str,
        db_type: str,
    ) -> dict[str, Any]:
        """Extract full metadata for a single table."""
        # --- Columns ---
        raw_columns = inspector.get_columns(table_name)
        columns = []
        for col in raw_columns:
            type_str = str(col["type"]).upper()
            col_info: dict[str, Any] = {
                "name": col["name"],
                "type": str(col["type"]),
                "nullable": col.get("nullable", True),
                "default": str(col.get("default", "")) if col.get("default") is not None else None,
                "comment": col.get("comment") or "",
                "sample_values": None,
            }

            # Sample values for likely categorical / code columns
            if any(type_str.startswith(p) for p in CATEGORICAL_TYPE_PREFIXES):
                col_info["sample_values"] = self._get_sample_values(
                    engine, table_name, col["name"]
                )

            columns.append(col_info)

        # --- Primary key ---
        pk_info = inspector.get_pk_constraint(table_name)
        primary_key = pk_info.get("constrained_columns", [])

        # --- Foreign keys ---
        raw_fks = inspector.get_foreign_keys(table_name)
        foreign_keys = [
            {
                "constrained_columns": fk["constrained_columns"],
                "referred_table": fk["referred_table"],
                "referred_columns": fk["referred_columns"],
            }
            for fk in raw_fks
        ]

        # --- Indexes ---
        raw_indexes = inspector.get_indexes(table_name)
        indexes = [
            {
                "name": idx.get("name"),
                "columns": idx.get("column_names", []),
                "unique": idx.get("unique", False),
            }
            for idx in raw_indexes
        ]

        # --- Table comment ---
        try:
            comment_info = inspector.get_table_comment(table_name)
            table_comment = comment_info.get("text") or ""
        except Exception:
            table_comment = ""

        # --- Row count (best-effort, with timeout) ---
        row_count = self._get_row_count(engine, table_name)

        return {
            "name": table_name,
            "comment": table_comment,
            "columns": columns,
            "primary_key": primary_key,
            "foreign_keys": foreign_keys,
            "indexes": indexes,
            "row_count": row_count,
        }

    def _get_sample_values(
        self, engine: sa.Engine, table: str, column: str
    ) -> list[str]:
        """Get distinct non-null sample values for a column."""
        try:
            # Quote identifiers to handle reserved words and mixed case
            q_table = self._quote(engine, table)
            q_col = self._quote(engine, column)
            dialect = engine.dialect.name
            if dialect == "mssql":
                sql = (
                    f"SELECT DISTINCT TOP {self.sample_values_limit} {q_col} "
                    f"FROM {q_table} WHERE {q_col} IS NOT NULL"
                )
            else:
                sql = (
                    f"SELECT DISTINCT {q_col} FROM {q_table} "
                    f"WHERE {q_col} IS NOT NULL "
                    f"LIMIT {self.sample_values_limit}"
                )
            with engine.connect() as conn:
                result = conn.execute(text(sql))
                return [str(row[0]) for row in result if row[0] is not None]
        except Exception as e:
            logger.debug(f"Could not sample {table}.{column}: {e}")
            return []

    def _get_row_count(self, engine: sa.Engine, table: str) -> int:
        """Approximate row count; returns -1 on failure."""
        try:
            q_table = self._quote(engine, table)
            with engine.connect() as conn:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {q_table}"))
                return result.scalar() or 0
        except Exception as e:
            logger.debug(f"Could not count rows in {table}: {e}")
            return -1

    def _quote(self, engine: sa.Engine, identifier: str) -> str:
        """Return a properly quoted identifier for the target dialect."""
        return engine.dialect.identifier_preparer.quote(identifier)

    def _extract_relationships(
        self, tables: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Build a flat list of FK relationships across all tables."""
        relationships = []
        for table_name, table_info in tables.items():
            for fk in table_info.get("foreign_keys", []):
                from_cols = ", ".join(fk["constrained_columns"])
                to_cols = ", ".join(fk["referred_columns"])
                relationships.append({
                    "from_table": table_name,
                    "from_columns": fk["constrained_columns"],
                    "to_table": fk["referred_table"],
                    "to_columns": fk["referred_columns"],
                    # Pre-formatted JOIN hint for the LLM prompt
                    "join_hint": (
                        f"{table_name}.{from_cols} = "
                        f"{fk['referred_table']}.{to_cols}"
                    ),
                })
        return relationships

    def _build_summary(
        self, tables: dict[str, Any], db_type: str
    ) -> dict[str, Any]:
        counted = [t["row_count"] for t in tables.values() if t.get("row_count", -1) >= 0]
        return {
            "db_type": db_type,
            "table_count": len(tables),
            "total_rows_estimate": sum(counted),
            "table_names": list(tables.keys()),
        }
