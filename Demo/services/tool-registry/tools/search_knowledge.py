"""
Tool: search_knowledge
Search knowledge base using vector similarity (RAG)
"""
from typing import Dict, Any, Optional
import logging
import requests
from database import db
from config import settings

logger = logging.getLogger(__name__)


def search_knowledge(
    query: str,
    limit: int = 5,
    category: Optional[str] = None
) -> Dict[str, Any]:
    """
    Search knowledge base for relevant documents using semantic similarity

    Args:
        query: Natural language search query
        limit: Maximum number of results to return (default: 5)
        category: Optional category filter (e.g., "policy", "procedure", "diagnosis_code")

    Returns:
        Dict with:
            - documents: List of relevant documents with title, content, similarity score
            - count: Number of results found
            - query: The original search query
    """
    logger.info(f"Searching knowledge base: '{query}' (limit={limit}, category={category})")

    try:
        # Step 1: Generate embedding for the query via LLM Gateway
        embed_response = requests.post(
            f"{settings.llm_gateway_url}/llm/embed",
            json={"text": query},
            timeout=30
        )
        embed_response.raise_for_status()
        embed_data = embed_response.json()

        query_embedding = embed_data["embeddings"][0]
        embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

        # Step 2: Query pgvector for similar documents
        if category:
            search_query = """
                SELECT
                    doc_id,
                    title,
                    content,
                    metadata,
                    1 - (embedding <=> %s::vector) AS similarity
                FROM knowledge_base
                WHERE embedding IS NOT NULL
                  AND metadata->>'category' = %s
                  AND 1 - (embedding <=> %s::vector) > 0.3
                ORDER BY embedding <=> %s::vector
                LIMIT %s
            """
            params = (embedding_str, category, embedding_str, embedding_str, limit)
        else:
            search_query = """
                SELECT
                    doc_id,
                    title,
                    content,
                    metadata,
                    1 - (embedding <=> %s::vector) AS similarity
                FROM knowledge_base
                WHERE embedding IS NOT NULL
                  AND 1 - (embedding <=> %s::vector) > 0.3
                ORDER BY embedding <=> %s::vector
                LIMIT %s
            """
            params = (embedding_str, embedding_str, embedding_str, limit)

        results = db.execute_query(search_query, params)

        # Format results
        documents = []
        for row in results:
            doc = {
                "doc_id": row["doc_id"],
                "title": row["title"],
                "content": row["content"],
                "category": row["metadata"].get("category", "unknown") if row["metadata"] else "unknown",
                "tags": row["metadata"].get("tags", []) if row["metadata"] else [],
                "similarity": round(float(row["similarity"]), 4)
            }
            documents.append(doc)

        logger.info(f"Found {len(documents)} relevant documents for '{query}'")

        return {
            "documents": documents,
            "count": len(documents),
            "query": query
        }

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to generate query embedding: {e}")
        raise RuntimeError(f"Embedding service unavailable: {e}")
    except Exception as e:
        logger.error(f"Knowledge search error: {e}", exc_info=True)
        raise
