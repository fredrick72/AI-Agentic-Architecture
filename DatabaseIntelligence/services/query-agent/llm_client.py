"""
LLM Client

Thin wrapper around the OpenAI Chat Completions API.
Abstracts model selection and returns structured responses with token counts.
"""
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Models used by role
SQL_GENERATION_MODEL = "gpt-4o"          # Best SQL accuracy
EXPLANATION_MODEL = "gpt-4o-mini"        # Cheaper for plain-language summaries


class LLMClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    def generate_sql(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        """
        Call GPT-4o to generate SQL.  Temperature 0 for deterministic output.
        Returns { response, model, input_tokens, output_tokens, cost_usd }
        """
        return self._complete(
            model=SQL_GENERATION_MODEL,
            system_prompt=system_prompt,
            user_message=user_message,
            temperature=temperature,
            max_tokens=800,
        )

    def explain_results(
        self,
        system_prompt: str,
        user_message: str,
    ) -> dict[str, Any]:
        """
        Call GPT-4o-mini to explain query results in plain language.
        Returns { response, model, input_tokens, output_tokens, cost_usd }
        """
        return self._complete(
            model=EXPLANATION_MODEL,
            system_prompt=system_prompt,
            user_message=user_message,
            temperature=0.3,
            max_tokens=500,
        )

    def _complete(
        self,
        model: str,
        system_prompt: str,
        user_message: str,
        temperature: float,
        max_tokens: int,
    ) -> dict[str, Any]:
        with httpx.Client(timeout=60) as client:
            resp = client.post(
                "https://api.openai.com/v1/chat/completions",
                headers=self._headers,
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        content = data["choices"][0]["message"]["content"].strip()
        usage = data.get("usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)

        # Approximate cost
        cost = self._estimate_cost(model, input_tokens, output_tokens)

        return {
            "response": content,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": cost,
        }

    def _estimate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        # Prices per 1M tokens (as of early 2025)
        pricing = {
            "gpt-4o":       {"input": 2.50,  "output": 10.00},
            "gpt-4o-mini":  {"input": 0.15,  "output": 0.60},
            "gpt-4-turbo":  {"input": 10.00, "output": 30.00},
        }
        rates = pricing.get(model, {"input": 2.50, "output": 10.00})
        return (
            (input_tokens * rates["input"] + output_tokens * rates["output"]) / 1_000_000
        )
