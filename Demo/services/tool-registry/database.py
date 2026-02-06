"""
Tool Registry - Database Connection
"""
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Any, Optional
from contextlib import contextmanager
import logging
from config import settings

logger = logging.getLogger(__name__)


class Database:
    """PostgreSQL database connection manager"""

    def __init__(self):
        """Initialize database connection pool"""
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
        Get database connection context manager

        Usage:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM patients")
        """
        conn = None
        try:
            conn = psycopg2.connect(**self.connection_params)
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def execute_query(
        self,
        query: str,
        params: Optional[tuple] = None,
        fetch_one: bool = False
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Execute a SELECT query and return results

        Args:
            query: SQL query string
            params: Query parameters (for prepared statements)
            fetch_one: If True, return only first row

        Returns:
            List of dicts (rows) or single dict if fetch_one=True
        """
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(query, params or ())

            if fetch_one:
                result = cursor.fetchone()
                return dict(result) if result else None
            else:
                results = cursor.fetchall()
                return [dict(row) for row in results]

    def execute_update(
        self,
        query: str,
        params: Optional[tuple] = None
    ) -> int:
        """
        Execute an INSERT/UPDATE/DELETE query

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            Number of rows affected
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params or ())
            return cursor.rowcount

    def test_connection(self) -> bool:
        """
        Test database connection

        Returns:
            True if connection successful
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                return result[0] == 1
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False


# Global database instance
db = Database()
