"""
Knowledge Store

Embeds schema chunks and stores them in pgvector for RAG retrieval.
Each table gets one chunk: the table description + formatted schema block.

Retrieval is by cosine similarity: given a user's question, find the
N most relevant tables and return their schema blocks for the SQL prompt.
"""
import json
import logging
import uuid
from typing import Any

import httpx
import psycopg2
import psycopg2.extras

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "text-embedding-ada-002"
EMBEDDING_DIM = 1536


class KnowledgeStore:
    """Persist and retrieve schema chunks using pgvector."""

    def __init__(self, postgres_url: str, openai_api_key: str):
        self.postgres_url = postgres_url
        self.api_key = openai_api_key

    # ------------------------------------------------------------------ #
    #  Ingestion                                                           #
    # ------------------------------------------------------------------ #

    def store_schema(
        self, connection_id: str, schema_map: dict[str, Any]
    ) -> int:
        """
        Embed and store all table chunks for a connection.
        Deletes any previous chunks for this connection first.
        Returns the number of chunks stored.
        """
        tables = schema_map.get("tables", {})
        relationships = schema_map.get("relationships", [])

        # Build the text we'll embed for each table:
        #   description (natural language) + schema_block (structured)
        chunks: list[dict[str, Any]] = []
        for table_name, table_info in tables.items():
            if table_info.get("error"):
                continue

            description = table_info.get("description", "")
            schema_block = table_info.get("schema_block", "")
            embed_text = f"{description}\n\n{schema_block}"

            chunks.append({
                "connection_id": connection_id,
                "table_name": table_name,
                "chunk_type": "table_overview",
                "content": embed_text,
                "raw_schema": json.dumps(table_info),
                "metadata": {
                    "row_count": table_info.get("row_count", -1),
                    "column_count": len(table_info.get("columns", [])),
                    "has_fks": len(table_info.get("foreign_keys", [])) > 0,
                },
            })

        if not chunks:
            logger.warning("No chunks to embed (all tables errored?)")
            return 0

        # Embed all chunks in batches
        texts = [c["content"] for c in chunks]
        embeddings = self._embed_batch(texts)

        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                # Clear old chunks
                cur.execute(
                    "DELETE FROM schema_chunks WHERE connection_id = %s",
                    (connection_id,)
                )

                # Insert new chunks
                for chunk, embedding in zip(chunks, embeddings):
                    cur.execute(
                        """
                        INSERT INTO schema_chunks
                            (id, connection_id, table_name, chunk_type,
                             content, raw_schema, embedding, metadata)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            str(uuid.uuid4()),
                            chunk["connection_id"],
                            chunk["table_name"],
                            chunk["chunk_type"],
                            chunk["content"],
                            chunk["raw_schema"],
                            str(embedding),          # pgvector expects '[1,2,3,...]' string
                            json.dumps(chunk["metadata"]),
                        )
                    )

            conn.commit()
            logger.info(f"Stored {len(chunks)} schema chunks for connection {connection_id}")
            return len(chunks)
        finally:
            conn.close()

    # ------------------------------------------------------------------ #
    #  Retrieval                                                           #
    # ------------------------------------------------------------------ #

    def retrieve_relevant_tables(
        self,
        connection_id: str,
        query: str,
        top_k: int = 6,
    ) -> list[dict[str, Any]]:
        """
        Given a natural-language query, return the top_k most relevant
        table schema blocks (by cosine similarity to the query embedding).

        Returns list of:
            { table_name, content, schema_block, raw_schema, similarity }
        """
        query_embedding = self._embed_single(query)

        conn = self._get_conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT
                        table_name,
                        content,
                        raw_schema,
                        1 - (embedding <=> %s::vector) AS similarity
                    FROM schema_chunks
                    WHERE connection_id = %s
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                    """,
                    (str(query_embedding), connection_id, str(query_embedding), top_k)
                )
                rows = cur.fetchall()
                return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_all_table_names(self, connection_id: str) -> list[str]:
        """Return all crawled table names for a connection (for the schema explorer)."""
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT table_name FROM schema_chunks
                    WHERE connection_id = %s
                    ORDER BY table_name
                    """,
                    (connection_id,)
                )
                return [row[0] for row in cur.fetchall()]
        finally:
            conn.close()

    def get_table_schema(
        self, connection_id: str, table_name: str
    ) -> dict[str, Any] | None:
        """Return the raw schema JSON for a specific table."""
        conn = self._get_conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT raw_schema FROM schema_chunks
                    WHERE connection_id = %s AND table_name = %s
                    LIMIT 1
                    """,
                    (connection_id, table_name)
                )
                row = cur.fetchone()
                if row:
                    raw = row["raw_schema"]
                    # Handle both string and already-parsed dict
                    if isinstance(raw, str):
                        return json.loads(raw)
                    return raw
                return None
        finally:
            conn.close()

    # ------------------------------------------------------------------ #
    #  Embedding helpers                                                   #
    # ------------------------------------------------------------------ #

    def _embed_single(self, text: str) -> list[float]:
        return self._embed_batch([text])[0]

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Call OpenAI embeddings API. Batches up to 100 texts."""
        all_embeddings = []
        batch_size = 100

        with httpx.Client(timeout=60) as client:
            for i in range(0, len(texts), batch_size):
                batch = texts[i : i + batch_size]
                # Truncate very long texts (ada-002 limit: ~8191 tokens)
                batch = [t[:6000] for t in batch]

                resp = client.post(
                    "https://api.openai.com/v1/embeddings",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={"model": EMBEDDING_MODEL, "input": batch},
                )
                resp.raise_for_status()
                data = resp.json()
                batch_embeddings = [item["embedding"] for item in data["data"]]
                all_embeddings.extend(batch_embeddings)

        return all_embeddings

    # ------------------------------------------------------------------ #
    #  DB connection                                                       #
    # ------------------------------------------------------------------ #

    def _get_conn(self):
        return psycopg2.connect(self.postgres_url)
