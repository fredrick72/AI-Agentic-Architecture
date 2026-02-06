"""
LLM Gateway - Model Selection
Intelligently routes requests to GPT-4 (expensive, smart) or GPT-3.5 (cheap, fast)
"""
import re
from typing import Dict, Tuple
from config import settings
import logging

logger = logging.getLogger(__name__)


class ModelSelector:
    """Selects optimal model based on prompt complexity"""

    # Keywords indicating complex reasoning needs
    COMPLEX_KEYWORDS = [
        "analyze", "explain", "compare", "evaluate", "assess",
        "design", "architect", "plan", "strategy", "optimize",
        "philosophical", "theoretical", "implications", "consequences",
        "synthesize", "elaborate", "comprehensive", "detailed",
        "multi-step", "complex", "intricate", "nuanced"
    ]

    # Keywords indicating simple queries
    SIMPLE_KEYWORDS = [
        "what is", "define", "list", "show", "find",
        "count", "sum", "calculate", "total", "how many",
        "yes or no", "true or false", "lookup", "fetch"
    ]

    def __init__(self):
        """Initialize model selector"""
        self.gpt4_model = settings.gpt4_turbo_model
        self.gpt35_model = settings.gpt35_turbo_model

    def select_model(
        self,
        prompt: str,
        context: Dict = None,
        user_preference: str = None
    ) -> Tuple[str, float, str]:
        """
        Select optimal model based on prompt complexity

        Args:
            prompt: User prompt text
            context: Optional context dict
            user_preference: Optional user-specified model preference

        Returns:
            Tuple of (model_name, complexity_score, reason)
        """
        # Honor user preference if provided
        if user_preference:
            if "gpt-4" in user_preference.lower():
                return (self.gpt4_model, 1.0, "User requested GPT-4")
            elif "gpt-3.5" in user_preference.lower():
                return (self.gpt35_model, 0.0, "User requested GPT-3.5")

        # Calculate complexity score
        complexity_score = self._calculate_complexity(prompt)

        # Select model based on thresholds
        if complexity_score >= settings.complexity_threshold_high:
            model = self.gpt4_model
            reason = f"High complexity ({complexity_score:.2f}) - requires advanced reasoning"
        elif complexity_score >= settings.complexity_threshold_medium:
            model = self.gpt35_model
            reason = f"Medium complexity ({complexity_score:.2f}) - standard model sufficient"
        else:
            model = self.gpt35_model
            reason = f"Low complexity ({complexity_score:.2f}) - simple query"

        logger.info(f"Selected {model}: {reason}")
        return (model, complexity_score, reason)

    def _calculate_complexity(self, prompt: str) -> float:
        """
        Calculate complexity score (0.0 - 1.0)

        Factors:
        - Prompt length
        - Presence of complex keywords
        - Question complexity (multiple questions, nested clauses)
        - Technical terminology density

        Args:
            prompt: Input prompt text

        Returns:
            Complexity score between 0.0 and 1.0
        """
        prompt_lower = prompt.lower()
        score = 0.0

        # Factor 1: Length-based complexity (max 0.3)
        word_count = len(prompt.split())
        if word_count > 100:
            score += 0.3
        elif word_count > 50:
            score += 0.2
        elif word_count > 20:
            score += 0.1

        # Factor 2: Complex keywords (max 0.4)
        complex_matches = sum(
            1 for keyword in self.COMPLEX_KEYWORDS
            if keyword in prompt_lower
        )
        score += min(complex_matches * 0.1, 0.4)

        # Factor 3: Simple keywords reduce score (max -0.3)
        simple_matches = sum(
            1 for keyword in self.SIMPLE_KEYWORDS
            if keyword in prompt_lower
        )
        score -= min(simple_matches * 0.1, 0.3)

        # Factor 4: Multiple questions or clauses (max 0.2)
        question_marks = prompt.count("?")
        if question_marks > 2:
            score += 0.2
        elif question_marks > 1:
            score += 0.1

        # Factor 5: Nested clauses and conjunctions (max 0.1)
        complex_conjunctions = ["however", "moreover", "furthermore", "whereas", "although"]
        if any(conj in prompt_lower for conj in complex_conjunctions):
            score += 0.1

        # Normalize score to 0.0 - 1.0 range
        score = max(0.0, min(1.0, score))

        return round(score, 2)

    def get_model_info(self, model: str) -> Dict:
        """
        Get information about a model

        Args:
            model: Model name

        Returns:
            Dict with model metadata
        """
        if "gpt-4" in model.lower():
            return {
                "name": model,
                "family": "GPT-4",
                "input_cost_per_1k": settings.gpt4_turbo_input_cost,
                "output_cost_per_1k": settings.gpt4_turbo_output_cost,
                "description": "Advanced reasoning, complex tasks",
                "context_window": 128000,
                "training_cutoff": "Apr 2023"
            }
        else:  # GPT-3.5
            return {
                "name": model,
                "family": "GPT-3.5",
                "input_cost_per_1k": settings.gpt35_turbo_input_cost,
                "output_cost_per_1k": settings.gpt35_turbo_output_cost,
                "description": "Fast, cost-effective for simple tasks",
                "context_window": 16385,
                "training_cutoff": "Sep 2021"
            }


# Global model selector instance
model_selector = ModelSelector()
