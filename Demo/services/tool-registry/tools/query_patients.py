"""
Tool: query_patients
Search for patients by name with fuzzy matching
"""
from typing import List, Dict, Any, Optional
import logging
from database import db

logger = logging.getLogger(__name__)


def query_patients(name: str, limit: int = 10) -> Dict[str, Any]:
    """
    Search for patients by name (fuzzy matching)

    Args:
        name: Patient name to search for (partial match supported)
        limit: Maximum number of results to return

    Returns:
        Dict with:
            - patients: List of matching patient records
            - count: Number of matches found
            - search_term: The search term used

    Example:
        >>> result = query_patients("John")
        >>> result['count']
        3
        >>> result['patients'][0]['full_name']
        'John Smith'
    """
    logger.info(f"Searching for patients: '{name}' (limit={limit})")

    try:
        # Use ILIKE for case-insensitive pattern matching
        query = """
            SELECT
                patient_id,
                full_name,
                first_name,
                last_name,
                dob,
                email,
                phone,
                last_visit_date,
                metadata
            FROM patients
            WHERE
                full_name ILIKE %s
                OR first_name ILIKE %s
                OR last_name ILIKE %s
            ORDER BY
                last_visit_date DESC NULLS LAST,
                full_name ASC
            LIMIT %s
        """

        # Add wildcards for partial matching
        search_pattern = f"%{name}%"
        params = (search_pattern, search_pattern, search_pattern, limit)

        results = db.execute_query(query, params)

        # Format results
        patients = []
        for row in results:
            # Convert date objects to strings
            patient = {
                "patient_id": row["patient_id"],
                "full_name": row["full_name"],
                "first_name": row["first_name"],
                "last_name": row["last_name"],
                "dob": row["dob"].isoformat() if row["dob"] else None,
                "email": row["email"],
                "phone": row["phone"],
                "last_visit_date": row["last_visit_date"].isoformat() if row["last_visit_date"] else None,
                "metadata": row["metadata"]
            }
            patients.append(patient)

        logger.info(f"Found {len(patients)} patients matching '{name}'")

        return {
            "patients": patients,
            "count": len(patients),
            "search_term": name
        }

    except Exception as e:
        logger.error(f"Error querying patients: {e}", exc_info=True)
        raise


def get_patient_by_id(patient_id: str) -> Optional[Dict[str, Any]]:
    """
    Get patient by exact ID

    Args:
        patient_id: Patient ID (e.g., "PAT-12345")

    Returns:
        Patient dict or None if not found
    """
    logger.info(f"Looking up patient: {patient_id}")

    try:
        query = """
            SELECT
                patient_id,
                full_name,
                first_name,
                last_name,
                dob,
                email,
                phone,
                last_visit_date,
                metadata
            FROM patients
            WHERE patient_id = %s
        """

        result = db.execute_query(query, (patient_id,), fetch_one=True)

        if result:
            # Convert date objects to strings
            patient = {
                "patient_id": result["patient_id"],
                "full_name": result["full_name"],
                "first_name": result["first_name"],
                "last_name": result["last_name"],
                "dob": result["dob"].isoformat() if result["dob"] else None,
                "email": result["email"],
                "phone": result["phone"],
                "last_visit_date": result["last_visit_date"].isoformat() if result["last_visit_date"] else None,
                "metadata": result["metadata"]
            }
            logger.info(f"Found patient: {patient['full_name']}")
            return patient
        else:
            logger.warning(f"Patient not found: {patient_id}")
            return None

    except Exception as e:
        logger.error(f"Error getting patient by ID: {e}", exc_info=True)
        raise
