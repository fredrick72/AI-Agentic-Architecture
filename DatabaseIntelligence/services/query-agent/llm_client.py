"""
LLM Client

Thin wrapper around the OpenAI Chat Completions API.
Abstracts model selection and returns structured responses with token counts.
"""
import logging
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class RateLimitError(Exception):
    """Raised when OpenAI rate limit is exceeded after retries."""
    pass

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
        max_retries: int = 3,
    ) -> dict[str, Any]:
        """
        Call OpenAI API with exponential backoff for rate limits.
        Retries on 429 (rate limit) and 503 (service unavailable).
        """
        last_error = None

        for attempt in range(max_retries):
            try:
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

                    # Handle rate limit errors with retry
                    if resp.status_code == 429:
                        retry_after = int(resp.headers.get("Retry-After", 2 ** attempt))
                        logger.warning(f"Rate limit hit (429). Attempt {attempt + 1}/{max_retries}. "
                                      f"Waiting {retry_after}s before retry...")
                        if attempt < max_retries - 1:
                            time.sleep(retry_after)
                            continue
                        else:
                            raise RateLimitError(
                                "OpenAI rate limit exceeded. Please wait a moment and try again."
                            )

                    # Handle temporary service issues
                    if resp.status_code == 503:
                        wait_time = 2 ** attempt
                        logger.warning(f"Service unavailable (503). Attempt {attempt + 1}/{max_retries}. "
                                      f"Waiting {wait_time}s...")
                        if attempt < max_retries - 1:
                            time.sleep(wait_time)
                            continue

                    resp.raise_for_status()
                    data = resp.json()

                # Success - parse response
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

            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code not in [429, 503]:
                    # Not a retryable error
                    raise
            except Exception as e:
                last_error = e
                logger.error(f"API call failed: {e}")
                raise

        # All retries exhausted
        if isinstance(last_error, httpx.HTTPStatusError) and last_error.response.status_code == 429:
            raise RateLimitError(
                "OpenAI rate limit exceeded after retries. Please wait a moment and try again."
            )
        raise last_error

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
