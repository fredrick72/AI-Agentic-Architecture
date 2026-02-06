"""
Database connection manager for Agent Runtime
"""
import psycopg2
import psycopg2.extras
import logging
from typing import List, Dict, Any, Optional
from contextlib import contextmanager

from config import settings

logger = logging.getLogger(__name__)


class Database:
    """Database connection manager with connection pooling"""

    def __init__(self):
        self.connection_params = {
            "host": settings.postgres_host,
            "port": settings.postgres_port,
            "database": settings.postgres_db,
            "user": settings.postgres_user,
            "password": settings.postgres_password,
        }
        logger.info(f"Database configured: {settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}")

    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections
        Automatically commits on success, rolls back on error
        """
        conn = None
        try:
            conn = psycopg2.connect(**self.connection_params)
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database error: {e}", exc_info=True)
            raise
        finally:
            if conn:
                conn.close()

    def execute_query(
        self,
        query: str,
        params: tuple = None,
        fetch_one: bool = False
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Execute SELECT query and return results as list of dicts

        Args:
            query: SQL query string
            params: Query parameters tuple
            fetch_one: If True, return single row instead of list

        Returns:
            List of dicts (or single dict if fetch_one=True)
        """
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, params)

                if fetch_one:
                    result = cur.fetchone()
                    return dict(result) if result else None
                else:
                    results = cur.fetchall()
                    return [dict(row) for row in results]

    def execute_update(
        self,
        query: str,
        params: tuple = None
    ) -> int:
        """
        Execute INSERT/UPDATE/DELETE query

        Args:
            query: SQL query string
            params: Query parameters tuple

        Returns:
            Number of affected rows
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                return cur.rowcount

    def test_connection(self) -> bool:
        """Test database connectivity"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    result = cur.fetchone()
                    return result[0] == 1
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False


# Global database instance
db = Database()
