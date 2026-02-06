"""
Tool: calculate_total
Calculate total amount from claim IDs or claim data
"""
from typing import List, Dict, Any, Optional
import logging
from database import db

logger = logging.getLogger(__name__)


def calculate_total(claim_ids: List[str]) -> Dict[str, Any]:
    """
    Calculate total amount for a list of claim IDs

    Args:
        claim_ids: List of claim IDs (e.g., ["CLM-12345-001", "CLM-12345-002"])

    Returns:
        Dict with:
            - total: Total amount
            - count: Number of claims
            - claim_ids: List of claim IDs processed
            - breakdown: List of individual amounts

    Example:
        >>> result = calculate_total(["CLM-12345-001", "CLM-12345-002"])
        >>> result['total']
        1700.50
        >>> result['count']
        2
    """
    logger.info(f"Calculating total for {len(claim_ids)} claims")

    if not claim_ids:
        return {
            "total": 0.0,
            "count": 0,
            "claim_ids": [],
            "breakdown": []
        }

    try:
        # Build query for multiple claim IDs
        placeholders = ','.join(['%s'] * len(claim_ids))
        query = f"""
            SELECT
                claim_id,
                amount,
                status,
                description
            FROM claims
            WHERE claim_id IN ({placeholders})
            ORDER BY claim_date DESC
        """

        results = db.execute_query(query, tuple(claim_ids))

        # Calculate total and build breakdown
        total = 0.0
        breakdown = []

        for row in results:
            amount = float(row["amount"])
            total += amount

            breakdown.append({
                "claim_id": row["claim_id"],
                "amount": amount,
                "status": row["status"],
                "description": row["description"]
            })

        # Check if all claim IDs were found
        found_ids = {row["claim_id"] for row in results}
        missing_ids = set(claim_ids) - found_ids

        if missing_ids:
            logger.warning(f"Claims not found: {missing_ids}")

        logger.info(
            f"Calculated total: ${total:.2f} from {len(results)}/{len(claim_ids)} claims"
        )

        return {
            "total": round(total, 2),
            "count": len(results),
            "claim_ids": claim_ids,
            "breakdown": breakdown,
            "missing_claim_ids": list(missing_ids) if missing_ids else []
        }

    except Exception as e:
        logger.error(f"Error calculating total: {e}", exc_info=True)
        raise


def calculate_total_by_patient(
    patient_id: str,
    status: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Calculate total claim amount for a patient

    Args:
        patient_id: Patient ID (e.g., "PAT-12345")
        status: Optional list of statuses to filter by

    Returns:
        Dict with total and breakdown by status

    Example:
        >>> result = calculate_total_by_patient("PAT-12345")
        >>> result['total']
        12450.50
        >>> result['by_status']['approved']
        11200.50
    """
    logger.info(f"Calculating total for patient: {patient_id}")

    try:
        # Build query
        query = """
            SELECT
                status,
                COUNT(*) as claim_count,
                SUM(amount) as total_amount
            FROM claims
            WHERE patient_id = %s
        """

        params = [patient_id]

        # Add status filter if provided
        if status:
            placeholders = ','.join(['%s'] * len(status))
            query += f" AND status IN ({placeholders})"
            params.extend(status)

        query += " GROUP BY status ORDER BY status"

        results = db.execute_query(query, tuple(params))

        # Aggregate results
        by_status = {}
        total = 0.0
        total_count = 0

        for row in results:
            status_name = row["status"]
            amount = float(row["total_amount"])
            count = int(row["claim_count"])

            by_status[status_name] = {
                "amount": round(amount, 2),
                "count": count
            }

            total += amount
            total_count += count

        logger.info(
            f"Patient {patient_id}: ${total:.2f} from {total_count} claims"
        )

        return {
            "patient_id": patient_id,
            "total": round(total, 2),
            "count": total_count,
            "by_status": by_status
        }

    except Exception as e:
        logger.error(f"Error calculating patient total: {e}", exc_info=True)
        raise
