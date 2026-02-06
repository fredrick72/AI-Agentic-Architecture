"""
Configuration for Agent Runtime
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings"""

    # Service configuration
    service_name: str = "agent-runtime"
    service_version: str = "1.0.0"
    log_level: str = "INFO"

    # Database configuration
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "agent_db"
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"

    # Service URLs
    llm_gateway_url: str = "http://llm-gateway:8002"
    tool_registry_url: str = "http://tool-registry:8003"
    clarification_engine_url: str = "http://clarification-engine:8004"

    # Agent configuration
    max_iterations: int = 5  # Max reasoning loop iterations
    max_conversation_history: int = 10  # Max turns to include in context
    enable_clarification: bool = True  # Enable clarification engine
    enable_cost_tracking: bool = True  # Track token costs

    # Timeouts (seconds)
    llm_timeout: int = 60
    tool_timeout: int = 30
    clarification_timeout: int = 10

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
