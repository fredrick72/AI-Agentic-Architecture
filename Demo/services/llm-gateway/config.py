"""
LLM Gateway - Configuration
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings from environment variables"""

    # OpenAI Configuration
    openai_api_key: str
    openai_organization: Optional[str] = None

    # Redis Configuration
    redis_url: str = "redis://redis:6379"
    cache_ttl_seconds: int = 300  # 5 minutes default

    # Model Configuration
    gpt4_turbo_model: str = "gpt-4-turbo-preview"
    gpt35_turbo_model: str = "gpt-3.5-turbo"

    # Cost Configuration (per 1,000 tokens)
    gpt4_turbo_input_cost: float = 0.01
    gpt4_turbo_output_cost: float = 0.03
    gpt35_turbo_input_cost: float = 0.0005
    gpt35_turbo_output_cost: float = 0.0015

    # Model Selection Thresholds
    complexity_threshold_high: float = 0.7  # Use GPT-4 if complexity > 0.7
    complexity_threshold_medium: float = 0.3  # Use GPT-3.5 if complexity > 0.3

    # Embedding Configuration
    embedding_model: str = "text-embedding-ada-002"
    embedding_cost_per_1k_tokens: float = 0.0001

    # Request Configuration
    max_tokens: int = 4000
    temperature: float = 0.7

    # Observability
    prometheus_enabled: bool = True
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
