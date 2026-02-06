"""
Configuration for Clarification Engine
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings"""

    # Service configuration
    service_name: str = "clarification-engine"
    service_version: str = "1.0.0"
    log_level: str = "INFO"

    # Database configuration
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "agent_db"
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"

    # LLM Gateway configuration
    llm_gateway_url: str = "http://llm-gateway:8002"

    # Clarification thresholds
    confidence_threshold_high: float = 0.85  # Above this = no clarification needed
    confidence_threshold_low: float = 0.40   # Below this = reject as unclear
    max_disambiguation_options: int = 10     # Max options to show user

    # Intent analysis
    use_llm_for_intent: bool = True          # Use LLM for intent analysis (vs rules)
    intent_analysis_model: str = "gpt-3.5-turbo"  # Cheaper model for analysis

    class Config:
        env_file = ".env"
        case_sensitive = False

    @property
    def database_url(self) -> str:
        """Construct database URL"""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
