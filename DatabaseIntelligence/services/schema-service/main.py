"""
Schema Intelligence Service

Provides:
  POST /connections          - Register a new database connection
  POST /connections/{id}/crawl - Crawl schema and build semantic map
  GET  /connections/{id}     - Get connection status + summary
  GET  /connections/{id}/tables - List all tables
  GET  /connections/{id}/tables/{table} - Get schema for one table
  POST /connections/{id}/search - RAG: find relevant tables for a query
"""
import json
import logging
import uuid
from datetime import datetime
from typing import Any, Optional

import psycopg2
import psycopg2.extras
from fastapi import FastAPI, HTTPException, BackgroundTasks, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from config import settings
from crawler import SchemaCrawler
from semantic_mapper import SemanticMapper
from knowledge_store import KnowledgeStore

logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Schema Intelligence Service",
    description="Crawls database schemas and builds semantic maps for RAG-powered SQL generation",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------------------------------------------ #
#  Request / Response models                                           #
# ------------------------------------------------------------------ #

class RegisterConnectionRequest(BaseModel):
    name: str = Field(..., description="Friendly name for this connection")
    connection_string: str = Field(
        ...,
        description="SQLAlchemy connection string, e.g. postgresql://user:pass@host/db"
    )


class SearchRequest(BaseModel):
    query: str = Field(..., description="Natural language question to find relevant tables for")
    top_k: int = Field(6, ge=1, le=20)


# ------------------------------------------------------------------ #
#  Helpers                                                             #
# ------------------------------------------------------------------ #

def get_db_conn():
    return psycopg2.connect(settings.postgres_url)


def detect_db_type(connection_string: str) -> str:
    cs = connection_string.lower()
    if cs.startswith("postgresql") or cs.startswith("postgres"):
        return "postgresql"
    elif cs.startswith("mysql"):
        return "mysql"
    elif cs.startswith("sqlite"):
        return "sqlite"
    elif cs.startswith("mssql") or cs.startswith("pyodbc"):
        return "mssql"
    return "unknown"


# ------------------------------------------------------------------ #
#  Background crawl task                                               #
# ------------------------------------------------------------------ #

def run_crawl(connection_id: str, connection_string: str, fingerprint: str | None = None):
    """
    Background task: crawl schema, enrich with LLM descriptions, embed and store.
    Updates connection status in the DB throughout.
    """
    db = get_db_conn()
    try:
        # Mark as crawling
        with db.cursor() as cur:
            cur.execute(
                "UPDATE connections SET status='crawling', updated_at=NOW() WHERE id=%s",
                (connection_id,)
            )
        db.commit()

        # 1. Crawl
        logger.info(f"[{connection_id}] Starting schema crawl...")
        crawler = SchemaCrawler(
            connection_string,
            sample_values_limit=settings.sample_values_limit
        )
        schema_map = crawler.crawl()

        # 2. Enrich with LLM descriptions
        logger.info(f"[{connection_id}] Generating semantic descriptions...")
        mapper = SemanticMapper(settings.openai_api_key)
        schema_map = mapper.enrich(schema_map)

        # 3. Embed and store
        logger.info(f"[{connection_id}] Embedding and storing schema chunks...")
        store = KnowledgeStore(settings.postgres_url, settings.openai_api_key)
        chunk_count = store.store_schema(connection_id, schema_map)

        # 4. Update connection as ready
        summary = schema_map.get("summary", {})
        with db.cursor() as cur:
            cur.execute(
                """UPDATE connections
                   SET status='ready',
                       schema_crawled_at=NOW(),
                       table_count=%s,
                       schema_fingerprint=%s,
                       updated_at=NOW()
                   WHERE id=%s""",
                (summary.get("table_count", 0), fingerprint, connection_id)
            )
        db.commit()
        logger.info(f"[{connection_id}] Crawl complete: {chunk_count} chunks stored")

    except Exception as e:
        logger.error(f"[{connection_id}] Crawl failed: {e}", exc_info=True)
        with db.cursor() as cur:
            cur.execute(
                """UPDATE connections
                   SET status='error', error_message=%s, updated_at=NOW()
                   WHERE id=%s""",
                (str(e)[:1000], connection_id)
            )
        db.commit()
    finally:
        db.close()


# ------------------------------------------------------------------ #
#  API Endpoints                                                       #
# ------------------------------------------------------------------ #

@app.get("/")
async def root():
    return {"service": "Schema Intelligence Service", "version": "1.0.0", "status": "operational"}


@app.get("/health")
async def health():
    try:
        conn = get_db_conn()
        conn.close()
        db_ok = True
    except Exception:
        db_ok = False
    return {
        "status": "healthy" if db_ok else "degraded",
        "database": "connected" if db_ok else "disconnected",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/connections", status_code=status.HTTP_201_CREATED)
async def register_connection(
    request: RegisterConnectionRequest,
    background_tasks: BackgroundTasks
):
    """
    Register a database connection and kick off a background crawl.
    If an existing ready connection with the same connection string and unchanged
    schema fingerprint is found, returns it immediately (no re-crawl).
    """
    # Test the connection before accepting
    crawler = SchemaCrawler(request.connection_string)
    ok, err = crawler.test_connection()
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Cannot connect to database: {err}"
        )

    # Compute schema fingerprint (fast — metadata only, no row sampling)
    try:
        fingerprint = crawler.compute_fingerprint()
    except Exception as fp_err:
        logger.warning(f"Could not compute fingerprint, will re-crawl: {fp_err}")
        fingerprint = None

    # Check for an existing ready connection with the same string + unchanged schema
    db = get_db_conn()
    try:
        with db.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """SELECT id AS connection_id, name, db_type, table_count, schema_fingerprint
                   FROM connections
                   WHERE connection_string = %s
                     AND status = 'ready'
                     AND schema_fingerprint IS NOT NULL
                   ORDER BY schema_crawled_at DESC LIMIT 1""",
                (request.connection_string,)
            )
            existing = cur.fetchone()
    finally:
        db.close()

    if existing and fingerprint and existing.get("schema_fingerprint") == fingerprint:
        logger.info(f"Fingerprint match — reusing connection {existing['connection_id']}")
        return {
            "connection_id": existing["connection_id"],
            "name": existing["name"],
            "db_type": existing["db_type"],
            "status": "ready",
            "message": "Schema unchanged — using cached analysis.",
        }

    # No match — insert new connection and crawl
    connection_id = str(uuid.uuid4())
    db_type = detect_db_type(request.connection_string)

    db = get_db_conn()
    try:
        with db.cursor() as cur:
            cur.execute(
                """INSERT INTO connections
                       (id, name, db_type, connection_string, status)
                   VALUES (%s, %s, %s, %s, 'pending')""",
                (connection_id, request.name, db_type, request.connection_string)
            )
        db.commit()
    finally:
        db.close()

    background_tasks.add_task(run_crawl, connection_id, request.connection_string, fingerprint)

    return {
        "connection_id": connection_id,
        "name": request.name,
        "db_type": db_type,
        "status": "crawling",
        "message": "Schema crawl started. Poll GET /connections/{id} for status.",
    }


@app.get("/connections/{connection_id}")
async def get_connection(connection_id: str):
    """Get connection status and summary."""
    db = get_db_conn()
    try:
        with db.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """SELECT id AS connection_id, name, db_type, status, table_count,
                          schema_crawled_at, error_message, created_at
                   FROM connections WHERE id = %s""",
                (connection_id,)
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Connection not found")
            return dict(row)
    finally:
        db.close()


@app.get("/connections/{connection_id}/tables")
async def list_tables(connection_id: str):
    """List all tables discovered for this connection."""
    store = KnowledgeStore(settings.postgres_url, settings.openai_api_key)
    tables = store.get_all_table_names(connection_id)
    return {"connection_id": connection_id, "tables": tables, "count": len(tables)}


@app.get("/connections/{connection_id}/tables/{table_name}")
async def get_table_schema(connection_id: str, table_name: str):
    """Get the full schema for a single table."""
    store = KnowledgeStore(settings.postgres_url, settings.openai_api_key)
    schema = store.get_table_schema(connection_id, table_name)
    if not schema:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
    return schema


@app.post("/connections/{connection_id}/search")
async def search_schema(connection_id: str, request: SearchRequest):
    """
    RAG search: given a natural-language question, return the most
    relevant table schema blocks to include in a SQL generation prompt.
    """
    store = KnowledgeStore(settings.postgres_url, settings.openai_api_key)
    results = store.retrieve_relevant_tables(
        connection_id, request.query, top_k=request.top_k
    )
    return {
        "query": request.query,
        "connection_id": connection_id,
        "results": results,
        "count": len(results)
    }


@app.post("/connections/{connection_id}/recrawl")
async def recrawl(connection_id: str, background_tasks: BackgroundTasks):
    """Re-crawl the schema for an existing connection."""
    db = get_db_conn()
    try:
        with db.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT connection_string FROM connections WHERE id = %s",
                (connection_id,)
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Connection not found")
            connection_string = row["connection_string"]
    finally:
        db.close()

    background_tasks.add_task(run_crawl, connection_id, connection_string)
    return {"status": "recrawl_started", "connection_id": connection_id}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8010, log_level=settings.log_level.lower())
