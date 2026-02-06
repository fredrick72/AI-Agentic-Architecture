"""
LLM Gateway - Token Counting and Cost Calculation
"""
import tiktoken
from typing import Dict, Tuple
from config import settings


class TokenCounter:
    """Handles token counting and cost calculation for different models"""

    def __init__(self):
        """Initialize encodings for different models"""
        # Use cl100k_base encoding for GPT-4 and GPT-3.5-turbo
        self.encoding = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in a text string

        Args:
            text: Input text to count tokens for

        Returns:
            Number of tokens
        """
        return len(self.encoding.encode(text))

    def count_messages_tokens(self, messages: list) -> int:
        """
        Count tokens in a list of messages (chat format)

        Args:
            messages: List of message dicts with 'role' and 'content'

        Returns:
            Total number of tokens including message formatting overhead
        """
        num_tokens = 0

        for message in messages:
            # Add 4 tokens for message formatting (<im_start>, role, <im_sep>, <im_end>)
            num_tokens += 4
            for key, value in message.items():
                num_tokens += self.count_tokens(str(value))
                if key == "name":  # If name is present, add 1 token
                    num_tokens += 1

        num_tokens += 2  # Add 2 tokens for assistant reply priming

        return num_tokens

    def calculate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int
    ) -> Dict[str, float]:
        """
        Calculate cost for a model invocation

        Args:
            model: Model name (e.g., "gpt-4-turbo-preview")
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Dict with input_cost, output_cost, and total_cost in USD
        """
        # Determine cost rates based on model
        if "gpt-4" in model.lower():
            input_rate = settings.gpt4_turbo_input_cost
            output_rate = settings.gpt4_turbo_output_cost
        else:  # GPT-3.5
            input_rate = settings.gpt35_turbo_input_cost
            output_rate = settings.gpt35_turbo_output_cost

        # Calculate costs (rates are per 1,000 tokens)
        input_cost = (input_tokens / 1000) * input_rate
        output_cost = (output_tokens / 1000) * output_rate
        total_cost = input_cost + output_cost

        return {
            "input_cost": round(input_cost, 6),
            "output_cost": round(output_cost, 6),
            "total_cost": round(total_cost, 6),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
        }

    def estimate_prompt_cost(
        self,
        prompt: str,
        model: str,
        estimated_completion_tokens: int = 500
    ) -> Dict[str, float]:
        """
        Estimate cost before making API call

        Args:
            prompt: Input prompt text
            model: Model name
            estimated_completion_tokens: Estimated response length

        Returns:
            Dict with estimated costs
        """
        input_tokens = self.count_tokens(prompt)
        return self.calculate_cost(model, input_tokens, estimated_completion_tokens)


# Global token counter instance
token_counter = TokenCounter()
