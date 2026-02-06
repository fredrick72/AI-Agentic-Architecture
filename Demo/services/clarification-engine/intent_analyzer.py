"""
Intent Analyzer - Detect ambiguity and analyze user intent
"""
import logging
import requests
from typing import Dict, Any, List, Optional
from config import settings

logger = logging.getLogger(__name__)


class IntentAnalyzer:
    """
    Analyzes user input to detect ambiguity and extract entities

    Uses LLM to understand intent and identify entities that need disambiguation
    """

    def __init__(self):
        self.llm_gateway_url = settings.llm_gateway_url
        self.confidence_threshold_high = settings.confidence_threshold_high
        self.confidence_threshold_low = settings.confidence_threshold_low

    def analyze_intent(
        self,
        user_input: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze user input to detect intent and entities

        Args:
            user_input: Raw user message
            context: Optional conversation context

        Returns:
            Dict with:
                - intent: Detected intent (e.g., "query_claims", "find_patient")
                - entities: List of detected entities with confidence
                - confidence: Overall confidence (0.0-1.0)
                - needs_clarification: Boolean
                - ambiguous_entities: List of entities that need clarification

        Example:
            >>> analyze_intent("Find claims for John")
            {
                "intent": "query_claims",
                "entities": [
                    {"type": "patient_name", "value": "John", "confidence": 0.45}
                ],
                "confidence": 0.45,
                "needs_clarification": True,
                "ambiguous_entities": ["patient_name"]
            }
        """
        logger.info(f"Analyzing intent: {user_input[:100]}...")

        context = context or {}

        # Prepare prompt for LLM
        analysis_prompt = self._build_analysis_prompt(user_input, context)

        try:
            # Call LLM Gateway for intent analysis
            response = self._call_llm(analysis_prompt)

            # Parse LLM response
            intent_data = self._parse_intent_response(response)

            # Determine if clarification needed
            intent_data["needs_clarification"] = self._needs_clarification(intent_data)

            logger.info(
                f"Intent: {intent_data['intent']}, "
                f"Confidence: {intent_data['confidence']:.2f}, "
                f"Needs clarification: {intent_data['needs_clarification']}"
            )

            return intent_data

        except Exception as e:
            logger.error(f"Intent analysis failed: {e}", exc_info=True)

            # Fallback to rule-based analysis
            return self._rule_based_analysis(user_input)

    def _build_analysis_prompt(
        self,
        user_input: str,
        context: Dict[str, Any]
    ) -> str:
        """Build prompt for LLM intent analysis"""

        prompt = f"""Analyze this user request and extract structured information.

User Request: "{user_input}"

Available Tools:
1. query_patients - Search patients by name
2. get_claims - Get claims for a specific patient ID
3. calculate_total - Calculate total amount from claim IDs

Extract:
1. Primary Intent: Which tool should be used?
2. Entities: What values are provided?
   - patient_name: Full or partial patient name
   - patient_id: Exact patient ID (e.g., PAT-12345)
   - claim_id: Exact claim ID (e.g., CLM-12345-001)
   - date_range: Date filters
   - status: Claim status (pending, approved, denied)
3. Confidence: How confident are you in each entity? (0.0-1.0)
   - High (0.85+): Exact ID or very specific value
   - Medium (0.50-0.85): Clear entity but might have multiple matches
   - Low (<0.50): Vague or ambiguous

Context from previous conversation: {context}

Respond in this JSON format:
{{
    "intent": "query_patients|get_claims|calculate_total",
    "entities": [
        {{"type": "patient_name", "value": "John", "confidence": 0.45}}
    ],
    "confidence": 0.45,
    "reasoning": "Brief explanation"
}}

Focus on detecting ambiguity. Names like "John" without an ID are likely ambiguous."""

        return prompt

    def _call_llm(self, prompt: str) -> str:
        """Call LLM Gateway for analysis"""

        endpoint = f"{self.llm_gateway_url}/llm/complete"

        payload = {
            "prompt": prompt,
            "model_preference": "fast",  # Use cheaper model for analysis
            "temperature": 0.1,  # Low temperature for consistency
            "max_tokens": 500,
            "use_cache": True
        }

        response = requests.post(endpoint, json=payload, timeout=30)
        response.raise_for_status()

        data = response.json()
        return data["response"]

    def _parse_intent_response(self, llm_response: str) -> Dict[str, Any]:
        """Parse JSON response from LLM"""

        import json

        # Extract JSON from response (handle markdown code blocks)
        response_text = llm_response.strip()

        if "```json" in response_text:
            start = response_text.find("```json") + 7
            end = response_text.find("```", start)
            response_text = response_text[start:end].strip()
        elif "```" in response_text:
            start = response_text.find("```") + 3
            end = response_text.find("```", start)
            response_text = response_text[start:end].strip()

        try:
            intent_data = json.loads(response_text)

            # Validate required fields
            if "intent" not in intent_data:
                raise ValueError("Missing 'intent' field")
            if "entities" not in intent_data:
                intent_data["entities"] = []
            if "confidence" not in intent_data:
                # Calculate confidence from entities
                if intent_data["entities"]:
                    confidences = [e.get("confidence", 0.5) for e in intent_data["entities"]]
                    intent_data["confidence"] = sum(confidences) / len(confidences)
                else:
                    intent_data["confidence"] = 0.5

            return intent_data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            raise

    def _needs_clarification(self, intent_data: Dict[str, Any]) -> bool:
        """
        Determine if clarification is needed based on confidence scores

        Rules:
        - Confidence < 0.40: Too vague, reject
        - Confidence 0.40-0.85: Needs clarification
        - Confidence > 0.85: Good to proceed
        """
        confidence = intent_data.get("confidence", 0.0)

        # Check if any entity has low confidence
        ambiguous_entities = []
        for entity in intent_data.get("entities", []):
            entity_confidence = entity.get("confidence", 0.0)

            if entity_confidence < self.confidence_threshold_high:
                ambiguous_entities.append(entity["type"])

        intent_data["ambiguous_entities"] = ambiguous_entities

        # Need clarification if confidence is medium (not too low, not high)
        return (
            self.confidence_threshold_low <= confidence < self.confidence_threshold_high
            and len(ambiguous_entities) > 0
        )

    def _rule_based_analysis(self, user_input: str) -> Dict[str, Any]:
        """
        Fallback rule-based analysis if LLM fails

        Uses simple keyword matching
        """
        logger.warning("Using fallback rule-based analysis")

        user_input_lower = user_input.lower()

        # Detect intent
        intent = "unknown"
        if any(kw in user_input_lower for kw in ["find", "search", "look for", "patient"]):
            intent = "query_patients"
        elif any(kw in user_input_lower for kw in ["claims", "get claims", "show claims"]):
            intent = "get_claims"
        elif any(kw in user_input_lower for kw in ["total", "sum", "calculate"]):
            intent = "calculate_total"

        # Extract simple entities
        entities = []

        # Look for patient names (very simple heuristic)
        words = user_input.split()
        for i, word in enumerate(words):
            if word.lower() in ["for", "by", "patient"] and i + 1 < len(words):
                potential_name = words[i + 1]
                if potential_name[0].isupper():  # Likely a name
                    entities.append({
                        "type": "patient_name",
                        "value": potential_name,
                        "confidence": 0.50  # Medium confidence
                    })

        confidence = 0.60 if intent != "unknown" else 0.30

        return {
            "intent": intent,
            "entities": entities,
            "confidence": confidence,
            "needs_clarification": confidence < self.confidence_threshold_high,
            "ambiguous_entities": [e["type"] for e in entities],
            "reasoning": "Fallback rule-based analysis"
        }
