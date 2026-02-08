"""
Tool: manage_knowledge
Add and manage documents in the knowledge base with auto-embedding
"""
from typing import Dict, Any, List, Optional
import logging
import json
import requests
from database import db
from config import settings

logger = logging.getLogger(__name__)


def add_document(
    title: str,
    content: str,
    category: str = "general",
    tags: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Add a document to the knowledge base with auto-generated embedding

    Args:
        title: Document title
        content: Document content (will be embedded)
        category: Document category (e.g., "policy", "procedure", "diagnosis_code")
        tags: Optional list of tags for filtering

    Returns:
        Dict with doc_id and confirmation
    """
    logger.info(f"Adding document: '{title}' (category={category})")

    try:
        # Generate embedding via LLM Gateway
        embed_response = requests.post(
            f"{settings.llm_gateway_url}/llm/embed",
            json={"text": content},
            timeout=30
        )
        embed_response.raise_for_status()
        embed_data = embed_response.json()

        embedding = embed_data["embeddings"][0]
        embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

        metadata = {
            "category": category,
            "tags": tags or [],
            "source": "manual"
        }

        # Insert into knowledge_base
        insert_query = """
            INSERT INTO knowledge_base (title, content, embedding, metadata)
            VALUES (%s, %s, %s::vector, %s)
            RETURNING doc_id
        """
        params = (title, content, embedding_str, json.dumps(metadata))

        result = db.execute_query(insert_query, params, fetch_one=True)

        logger.info(f"Document added: doc_id={result['doc_id']}")

        return {
            "doc_id": result["doc_id"],
            "title": title,
            "category": category,
            "embedding_tokens": embed_data["tokens_used"],
            "status": "created"
        }

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to generate embedding: {e}")
        raise RuntimeError(f"Embedding service unavailable: {e}")
    except Exception as e:
        logger.error(f"Error adding document: {e}", exc_info=True)
        raise


def generate_missing_embeddings() -> Dict[str, Any]:
    """
    Generate embeddings for knowledge_base rows that have NULL embeddings.
    Called on startup to embed seed data.

    Returns:
        Dict with count of documents processed
    """
    logger.info("Checking for documents missing embeddings...")

    try:
        # Find rows without embeddings
        query = "SELECT doc_id, title, content FROM knowledge_base WHERE embedding IS NULL"
        rows = db.execute_query(query)

        if not rows:
            logger.info("All documents already have embeddings")
            return {"processed": 0, "status": "up_to_date"}

        logger.info(f"Found {len(rows)} documents without embeddings, generating...")

        processed = 0
        errors = 0

        for row in rows:
            try:
                # Generate embedding
                embed_response = requests.post(
                    f"{settings.llm_gateway_url}/llm/embed",
                    json={"text": row["content"]},
                    timeout=30
                )
                embed_response.raise_for_status()
                embed_data = embed_response.json()

                embedding = embed_data["embeddings"][0]
                embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

                # Update the row
                update_query = """
                    UPDATE knowledge_base
                    SET embedding = %s::vector, updated_at = CURRENT_TIMESTAMP
                    WHERE doc_id = %s
                """
                db.execute_update(update_query, (embedding_str, row["doc_id"]))

                processed += 1
                logger.info(f"  Embedded: [{processed}/{len(rows)}] {row['title']}")

            except Exception as e:
                errors += 1
                logger.error(f"  Failed to embed doc_id={row['doc_id']}: {e}")

        logger.info(f"Embedding generation complete: {processed} processed, {errors} errors")

        return {
            "processed": processed,
            "errors": errors,
            "total": len(rows),
            "status": "completed"
        }

    except Exception as e:
        logger.error(f"Error generating embeddings: {e}", exc_info=True)
        return {"processed": 0, "errors": 1, "status": "error", "message": str(e)}
