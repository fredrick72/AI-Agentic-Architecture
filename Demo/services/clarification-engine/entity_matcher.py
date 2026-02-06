"""
Entity Matcher - Find multiple matches for ambiguous entities
"""
import logging
from typing import List, Dict, Any, Optional
from database import db
from config import settings

logger = logging.getLogger(__name__)


class EntityMatcher:
    """
    Finds multiple matches for ambiguous entities in the database

    When user provides vague input (e.g., "John"), this finds all possible
    matches and ranks them by relevance
    """

    def __init__(self):
        self.max_options = settings.max_disambiguation_options

    def find_patient_matches(
        self,
        patient_name: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Find all patients matching a name

        Args:
            patient_name: Full or partial patient name
            context: Optional context for ranking (e.g., recent activity)

        Returns:
            List of patient matches with relevance scores

        Example:
            >>> find_patient_matches("John")
            [
                {
                    "id": "PAT-12345",
                    "label": "John Smith",
                    "metadata": {
                        "full_name": "John Smith",
                        "last_visit_date": "2024-01-15",
                        "email": "john.smith@email.com"
                    },
                    "relevance": 0.92
                }
            ]
        """
        logger.info(f"Finding patient matches for: {patient_name}")

        try:
            # Query database for fuzzy matches
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
                    full_name
                LIMIT %s
            """

            search_pattern = f"%{patient_name}%"
            results = db.execute_query(
                query,
                (search_pattern, search_pattern, search_pattern, self.max_options)
            )

            if not results:
                logger.warning(f"No patients found matching: {patient_name}")
                return []

            # Format and rank results
            matches = []
            for row in results:
                relevance = self._calculate_patient_relevance(row, patient_name, context)

                match = {
                    "id": row["patient_id"],
                    "label": row["full_name"],
                    "metadata": {
                        "full_name": row["full_name"],
                        "patient_id": row["patient_id"],
                        "dob": row["dob"].isoformat() if row["dob"] else None,
                        "email": row["email"],
                        "phone": row["phone"],
                        "last_visit_date": row["last_visit_date"].isoformat() if row["last_visit_date"] else None,
                        "additional_info": row.get("metadata", {})
                    },
                    "relevance": relevance
                }

                matches.append(match)

            # Sort by relevance (descending)
            matches.sort(key=lambda x: x["relevance"], reverse=True)

            logger.info(f"Found {len(matches)} patient matches")
            return matches

        except Exception as e:
            logger.error(f"Error finding patient matches: {e}", exc_info=True)
            raise

    def find_claim_matches(
        self,
        search_criteria: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Find claims matching criteria

        Args:
            search_criteria: Dict with filters (patient_id, status, claim_type, etc.)
            context: Optional context for ranking

        Returns:
            List of claim matches
        """
        logger.info(f"Finding claim matches with criteria: {search_criteria}")

        try:
            # Build dynamic query
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
                    provider_name
                FROM claims
                WHERE 1=1
            """

            params = []

            # Add filters
            if "patient_id" in search_criteria:
                query += " AND patient_id = %s"
                params.append(search_criteria["patient_id"])

            if "status" in search_criteria:
                if isinstance(search_criteria["status"], list):
                    placeholders = ','.join(['%s'] * len(search_criteria["status"]))
                    query += f" AND status IN ({placeholders})"
                    params.extend(search_criteria["status"])
                else:
                    query += " AND status = %s"
                    params.append(search_criteria["status"])

            if "claim_type" in search_criteria:
                query += " AND claim_type = %s"
                params.append(search_criteria["claim_type"])

            query += f" ORDER BY claim_date DESC LIMIT {self.max_options}"

            results = db.execute_query(query, tuple(params))

            if not results:
                logger.warning(f"No claims found for criteria: {search_criteria}")
                return []

            # Format results
            matches = []
            for row in results:
                match = {
                    "id": row["claim_id"],
                    "label": f"{row['description']} - ${float(row['amount']):.2f}",
                    "metadata": {
                        "claim_id": row["claim_id"],
                        "patient_id": row["patient_id"],
                        "claim_date": row["claim_date"].isoformat() if row["claim_date"] else None,
                        "amount": float(row["amount"]),
                        "status": row["status"],
                        "claim_type": row["claim_type"],
                        "description": row["description"],
                        "diagnosis_code": row["diagnosis_code"],
                        "provider_name": row["provider_name"]
                    },
                    "relevance": 1.0  # All matching claims are equally relevant
                }
                matches.append(match)

            logger.info(f"Found {len(matches)} claim matches")
            return matches

        except Exception as e:
            logger.error(f"Error finding claim matches: {e}", exc_info=True)
            raise

    def _calculate_patient_relevance(
        self,
        patient: Dict[str, Any],
        search_term: str,
        context: Optional[Dict[str, Any]]
    ) -> float:
        """
        Calculate relevance score for a patient match

        Factors:
        - Exact name match vs partial
        - Recency of last visit
        - Context (e.g., previously selected patient)

        Returns:
            Relevance score (0.0-1.0)
        """
        score = 0.5  # Base score

        full_name = patient.get("full_name", "").lower()
        first_name = patient.get("first_name", "").lower()
        last_name = patient.get("last_name", "").lower()
        search_lower = search_term.lower()

        # Name matching
        if full_name == search_lower:
            score += 0.3  # Exact match
        elif first_name == search_lower or last_name == search_lower:
            score += 0.25  # Exact first/last name
        elif search_lower in full_name:
            score += 0.15  # Partial match

        # Recency of last visit
        last_visit = patient.get("last_visit_date")
        if last_visit:
            from datetime import datetime, timedelta
            if isinstance(last_visit, str):
                last_visit = datetime.fromisoformat(last_visit.split('T')[0])

            days_since_visit = (datetime.now() - last_visit).days

            if days_since_visit < 30:
                score += 0.2  # Recent visit
            elif days_since_visit < 90:
                score += 0.1  # Moderately recent
            elif days_since_visit < 180:
                score += 0.05  # Somewhat recent

        # Context boost (e.g., previously selected patient)
        if context:
            previous_patient_id = context.get("last_patient_id")
            if previous_patient_id == patient.get("patient_id"):
                score += 0.15  # Boost for previous selection

        # Cap at 1.0
        return min(score, 1.0)

    def validate_entity(
        self,
        entity_type: str,
        entity_value: str
    ) -> Dict[str, Any]:
        """
        Validate if an entity value exists and is unambiguous

        Args:
            entity_type: Type of entity (patient_id, claim_id, patient_name)
            entity_value: Value to validate

        Returns:
            Dict with:
                - valid: Boolean
                - unique: Boolean (True if only one match)
                - matches: List of matches (if multiple)

        Example:
            >>> validate_entity("patient_id", "PAT-12345")
            {"valid": True, "unique": True, "matches": [{"id": "PAT-12345", ...}]}

            >>> validate_entity("patient_name", "John")
            {"valid": True, "unique": False, "matches": [3 patients]}
        """
        logger.info(f"Validating {entity_type}: {entity_value}")

        try:
            if entity_type == "patient_id":
                # Exact ID lookup
                query = "SELECT * FROM patients WHERE patient_id = %s"
                result = db.execute_query(query, (entity_value,), fetch_one=True)

                if result:
                    return {
                        "valid": True,
                        "unique": True,
                        "matches": [{
                            "id": result["patient_id"],
                            "label": result["full_name"],
                            "metadata": result
                        }]
                    }
                else:
                    return {"valid": False, "unique": False, "matches": []}

            elif entity_type == "patient_name":
                # Fuzzy name search
                matches = self.find_patient_matches(entity_value)

                return {
                    "valid": len(matches) > 0,
                    "unique": len(matches) == 1,
                    "matches": matches
                }

            elif entity_type == "claim_id":
                # Exact claim ID lookup
                query = "SELECT * FROM claims WHERE claim_id = %s"
                result = db.execute_query(query, (entity_value,), fetch_one=True)

                if result:
                    return {
                        "valid": True,
                        "unique": True,
                        "matches": [{
                            "id": result["claim_id"],
                            "label": f"{result['description']} - ${float(result['amount']):.2f}",
                            "metadata": result
                        }]
                    }
                else:
                    return {"valid": False, "unique": False, "matches": []}

            else:
                logger.warning(f"Unknown entity type: {entity_type}")
                return {"valid": False, "unique": False, "matches": []}

        except Exception as e:
            logger.error(f"Error validating entity: {e}", exc_info=True)
            raise
