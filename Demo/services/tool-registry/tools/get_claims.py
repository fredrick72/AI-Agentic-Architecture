"""
Tool: get_claims
Retrieve claims for a patient with optional filters
"""
from typing import List, Dict, Any, Optional
import logging
from database import db

logger = logging.getLogger(__name__)


def get_claims(
    patient_id: str,
    status: Optional[List[str]] = None,
    claim_type: Optional[str] = None,
    limit: int = 100
) -> Dict[str, Any]:
    """
    Retrieve claims for a patient

    Args:
        patient_id: Patient ID (e.g., "PAT-12345")
        status: Optional list of statuses to filter by
                (e.g., ["pending", "approved"])
        claim_type: Optional claim type filter
                    (e.g., "medical", "dental", "vision", "prescription")
        limit: Maximum number of claims to return

    Returns:
        Dict with:
            - claims: List of claim records
            - count: Number of claims found
            - patient_id: Patient ID searched
            - total_amount: Sum of all claim amounts

    Example:
        >>> result = get_claims("PAT-12345", status=["approved"])
        >>> result['count']
        4
        >>> result['total_amount']
        12450.50
    """
    logger.info(
        f"Getting claims for patient: {patient_id} "
        f"(status={status}, type={claim_type}, limit={limit})"
    )

    try:
        # Build dynamic query based on filters
        query = """
            SELECT
                claim_id,
                patient_id,
                claim_date,
                amount,
                status,
                claim_type,
                description,
                diagnosis_code,
                provider_name,
                metadata,
                created_at,
                updated_at
            FROM claims
            WHERE patient_id = %s
        """

        params = [patient_id]

        # Add status filter if provided
        if status:
            placeholders = ','.join(['%s'] * len(status))
            query += f" AND status IN ({placeholders})"
            params.extend(status)

        # Add claim_type filter if provided
        if claim_type:
            query += " AND claim_type = %s"
            params.append(claim_type)

        # Order by date descending
        query += " ORDER BY claim_date DESC, created_at DESC"

        # Add limit
        query += " LIMIT %s"
        params.append(limit)

        results = db.execute_query(query, tuple(params))

        # Format results and calculate total
        claims = []
        total_amount = 0.0

        for row in results:
            claim = {
                "claim_id": row["claim_id"],
                "patient_id": row["patient_id"],
                "claim_date": row["claim_date"].isoformat() if row["claim_date"] else None,
                "amount": float(row["amount"]),
                "status": row["status"],
                "claim_type": row["claim_type"],
                "description": row["description"],
                "diagnosis_code": row["diagnosis_code"],
                "provider_name": row["provider_name"],
                "metadata": row["metadata"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
            }
            claims.append(claim)
            total_amount += claim["amount"]

        logger.info(
            f"Found {len(claims)} claims for patient {patient_id}, "
            f"total amount: ${total_amount:.2f}"
        )

        return {
            "claims": claims,
            "count": len(claims),
            "patient_id": patient_id,
            "total_amount": round(total_amount, 2),
            "filters_applied": {
                "status": status,
                "claim_type": claim_type
            }
        }

    except Exception as e:
        logger.error(f"Error getting claims: {e}", exc_info=True)
        raise


def get_claim_by_id(claim_id: str) -> Optional[Dict[str, Any]]:
    """
    Get claim by exact ID

    Args:
        claim_id: Claim ID (e.g., "CLM-12345-001")

    Returns:
        Claim dict or None if not found
    """
    logger.info(f"Looking up claim: {claim_id}")

    try:
        query = """
            SELECT
                claim_id,
                patient_id,
                claim_date,
                amount,
                status,
                claim_type,
                description,
                diagnosis_code,
                provider_name,
                metadata,
                created_at,
                updated_at
            FROM claims
            WHERE claim_id = %s
        """

        result = db.execute_query(query, (claim_id,), fetch_one=True)

        if result:
            claim = {
                "claim_id": result["claim_id"],
                "patient_id": result["patient_id"],
                "claim_date": result["claim_date"].isoformat() if result["claim_date"] else None,
                "amount": float(result["amount"]),
                "status": result["status"],
                "claim_type": result["claim_type"],
                "description": result["description"],
                "diagnosis_code": result["diagnosis_code"],
                "provider_name": result["provider_name"],
                "metadata": result["metadata"],
                "created_at": result["created_at"].isoformat() if result["created_at"] else None,
                "updated_at": result["updated_at"].isoformat() if result["updated_at"] else None,
            }
            logger.info(f"Found claim: {claim_id} for ${claim['amount']}")
            return claim
        else:
            logger.warning(f"Claim not found: {claim_id}")
            return None

    except Exception as e:
        logger.error(f"Error getting claim by ID: {e}", exc_info=True)
        raise
