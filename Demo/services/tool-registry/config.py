"""
Tool Registry - Configuration
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings from environment variables"""

    # PostgreSQL Configuration
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "agent_db"
    postgres_user: str = "postgres"
    postgres_password: str = "demo_password"

    # Observability
    prometheus_enabled: bool = True
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = False

    @property
    def database_url(self) -> str:
        """Get PostgreSQL connection URL"""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


# Global settings instance
settings = Settings()
