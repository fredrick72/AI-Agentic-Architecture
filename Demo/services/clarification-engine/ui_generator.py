"""
UI Generator - Generate UI schemas for clarification widgets
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class UIGenerator:
    """
    Generates UI schemas for frontend clarification widgets

    Creates structured JSON that frontend can render as:
    - Radio buttons (single selection)
    - Checkboxes (multiple selection)
    - Date pickers
    - Text inputs with suggestions
    """

    def generate_disambiguation_ui(
        self,
        entity_type: str,
        question: str,
        options: List[Dict[str, Any]],
        allow_multiple: bool = False
    ) -> Dict[str, Any]:
        """
        Generate UI for entity disambiguation

        Args:
            entity_type: Type of entity to disambiguate (patient, claim, etc.)
            question: Question to ask user
            options: List of options with id, label, metadata, relevance
            allow_multiple: Allow selecting multiple options

        Returns:
            UI schema dict

        Example:
            >>> generate_disambiguation_ui(
                    entity_type="patient",
                    question="I found 3 patients named John. Which one?",
                    options=[
                        {
                            "id": "PAT-12345",
                            "label": "John Smith",
                            "metadata": {"last_visit_date": "2024-01-15"},
                            "relevance": 0.92
                        }
                    ]
                )
            {
                "type": "entity_disambiguation",
                "entity_type": "patient",
                "question": "I found 3 patients named John. Which one?",
                "ui_type": "radio",
                "options": [
                    {
                        "id": "PAT-12345",
                        "label": "John Smith",
                        "sublabel": "Last visit: Jan 15, 2024",
                        "metadata": {...},
                        "recommended": True
                    }
                ],
                "allow_multiple": False
            }
        """
        logger.info(f"Generating disambiguation UI for {entity_type} with {len(options)} options")

        # Sort options by relevance
        sorted_options = sorted(options, key=lambda x: x.get("relevance", 0.0), reverse=True)

        # Format options for UI
        ui_options = []
        for i, option in enumerate(sorted_options):
            ui_option = {
                "id": option["id"],
                "label": option["label"],
                "sublabel": self._generate_sublabel(entity_type, option.get("metadata", {})),
                "metadata": option.get("metadata", {}),
                "recommended": i == 0,  # Top option is recommended
                "relevance": option.get("relevance", 0.0)
            }
            ui_options.append(ui_option)

        ui_schema = {
            "type": "entity_disambiguation",
            "entity_type": entity_type,
            "question": question,
            "ui_type": "checkbox" if allow_multiple else "radio",
            "options": ui_options,
            "allow_multiple": allow_multiple,
            "metadata": {
                "total_options": len(ui_options),
                "generated_at": datetime.utcnow().isoformat()
            }
        }

        return ui_schema

    def generate_parameter_elicitation_ui(
        self,
        parameter_name: str,
        question: str,
        parameter_type: str,
        suggestions: Optional[List[Any]] = None,
        required: bool = True
    ) -> Dict[str, Any]:
        """
        Generate UI for parameter elicitation (missing required parameter)

        Args:
            parameter_name: Name of missing parameter
            question: Question to ask user
            parameter_type: Type (string, date, number, array)
            suggestions: Optional suggested values
            required: Is this parameter required?

        Returns:
            UI schema dict

        Example:
            >>> generate_parameter_elicitation_ui(
                    parameter_name="status",
                    question="Which claim statuses do you want to see?",
                    parameter_type="array",
                    suggestions=["pending", "approved", "denied"]
                )
            {
                "type": "parameter_elicitation",
                "parameter_name": "status",
                "question": "Which claim statuses do you want to see?",
                "ui_type": "checkbox",
                "parameter_type": "array",
                "suggestions": ["pending", "approved", "denied"],
                "required": True
            }
        """
        logger.info(f"Generating parameter elicitation UI for: {parameter_name}")

        # Determine UI type based on parameter type
        ui_type_map = {
            "string": "text",
            "date": "date",
            "number": "number",
            "array": "checkbox" if suggestions else "text",
            "boolean": "checkbox"
        }

        ui_type = ui_type_map.get(parameter_type, "text")

        ui_schema = {
            "type": "parameter_elicitation",
            "parameter_name": parameter_name,
            "question": question,
            "ui_type": ui_type,
            "parameter_type": parameter_type,
            "suggestions": suggestions or [],
            "required": required,
            "metadata": {
                "generated_at": datetime.utcnow().isoformat()
            }
        }

        return ui_schema

    def generate_constraint_negotiation_ui(
        self,
        constraint: str,
        question: str,
        options: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate UI for constraint negotiation (too many results, limits, etc.)

        Args:
            constraint: Type of constraint (result_limit, export_size, etc.)
            question: Question to ask user
            options: List of options to choose from

        Returns:
            UI schema dict

        Example:
            >>> generate_constraint_negotiation_ui(
                    constraint="result_limit",
                    question="I found 150 claims. How would you like to proceed?",
                    options=[
                        {"id": "show_all", "label": "Show all 150 results"},
                        {"id": "limit_50", "label": "Show first 50 results"},
                        {"id": "refine", "label": "Add more filters to narrow down"}
                    ]
                )
        """
        logger.info(f"Generating constraint negotiation UI: {constraint}")

        ui_schema = {
            "type": "constraint_negotiation",
            "constraint": constraint,
            "question": question,
            "ui_type": "radio",
            "options": options,
            "metadata": {
                "generated_at": datetime.utcnow().isoformat()
            }
        }

        return ui_schema

    def generate_scope_guidance_ui(
        self,
        detected_intent: str,
        question: str,
        suggestions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate UI for scope guidance (out-of-scope or unclear requests)

        Args:
            detected_intent: What we think the user wants
            question: Clarifying question
            suggestions: Suggested alternative actions

        Returns:
            UI schema dict

        Example:
            >>> generate_scope_guidance_ui(
                    detected_intent="export_data",
                    question="It looks like you want to export data. I can help with:",
                    suggestions=[
                        {"id": "query", "label": "Query and view claims data"},
                        {"id": "calculate", "label": "Calculate claim totals"}
                    ]
                )
        """
        logger.info(f"Generating scope guidance UI: {detected_intent}")

        ui_schema = {
            "type": "scope_guidance",
            "detected_intent": detected_intent,
            "question": question,
            "ui_type": "radio",
            "suggestions": suggestions,
            "metadata": {
                "generated_at": datetime.utcnow().isoformat()
            }
        }

        return ui_schema

    def _generate_sublabel(
        self,
        entity_type: str,
        metadata: Dict[str, Any]
    ) -> str:
        """
        Generate sublabel for an option based on entity type and metadata

        Shows relevant details to help user distinguish between options
        """
        if entity_type == "patient":
            # Show ID and last visit date
            parts = []

            if "patient_id" in metadata:
                parts.append(f"ID: {metadata['patient_id']}")

            if "last_visit_date" in metadata and metadata["last_visit_date"]:
                try:
                    date_str = metadata["last_visit_date"]
                    if isinstance(date_str, str):
                        date_obj = datetime.fromisoformat(date_str.split('T')[0])
                        formatted_date = date_obj.strftime("%b %d, %Y")
                        parts.append(f"Last visit: {formatted_date}")
                except Exception:
                    pass

            if "email" in metadata and metadata["email"]:
                parts.append(metadata["email"])

            return " • ".join(parts) if parts else "No additional info"

        elif entity_type == "claim":
            # Show claim details
            parts = []

            if "claim_date" in metadata and metadata["claim_date"]:
                try:
                    date_str = metadata["claim_date"]
                    if isinstance(date_str, str):
                        date_obj = datetime.fromisoformat(date_str.split('T')[0])
                        formatted_date = date_obj.strftime("%b %d, %Y")
                        parts.append(formatted_date)
                except Exception:
                    pass

            if "status" in metadata:
                status = metadata["status"].capitalize()
                parts.append(f"Status: {status}")

            if "claim_type" in metadata:
                claim_type = metadata["claim_type"].capitalize()
                parts.append(claim_type)

            return " • ".join(parts) if parts else "No additional info"

        else:
            # Generic sublabel
            return metadata.get("description", "")

    def format_clarification_response(
        self,
        clarification_type: str,
        user_selection: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Format user's clarification response for consumption by agent

        Args:
            clarification_type: Type of clarification that was requested
            user_selection: User's selection from UI

        Returns:
            Formatted response for agent

        Example:
            >>> format_clarification_response(
                    "entity_disambiguation",
                    {"entity_type": "patient", "selected_id": "PAT-12345"}
                )
            {
                "resolved": True,
                "entity_type": "patient",
                "resolved_value": "PAT-12345",
                "additional_context": {...}
            }
        """
        logger.info(f"Formatting clarification response: {clarification_type}")

        if clarification_type == "entity_disambiguation":
            return {
                "resolved": True,
                "entity_type": user_selection.get("entity_type"),
                "resolved_value": user_selection.get("selected_id"),
                "resolved_label": user_selection.get("selected_label"),
                "additional_context": user_selection.get("metadata", {})
            }

        elif clarification_type == "parameter_elicitation":
            return {
                "resolved": True,
                "parameter_name": user_selection.get("parameter_name"),
                "resolved_value": user_selection.get("value"),
                "parameter_type": user_selection.get("parameter_type")
            }

        elif clarification_type == "constraint_negotiation":
            return {
                "resolved": True,
                "constraint": user_selection.get("constraint"),
                "selected_option": user_selection.get("selected_id"),
                "action": user_selection.get("action")
            }

        elif clarification_type == "scope_guidance":
            return {
                "resolved": True,
                "selected_action": user_selection.get("selected_id"),
                "new_intent": user_selection.get("new_intent")
            }

        else:
            return {
                "resolved": False,
                "error": f"Unknown clarification type: {clarification_type}"
            }
