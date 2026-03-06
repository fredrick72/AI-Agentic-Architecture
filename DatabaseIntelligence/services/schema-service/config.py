from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: str
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "dbintel"
    postgres_user: str = "postgres"
    postgres_password: str = "dbintel_password"
    redis_url: str = "redis://localhost:6379"
    log_level: str = "INFO"

    # Schema crawl limits
    sample_values_limit: int = 20       # Max distinct values to sample per column
    row_count_timeout_sec: int = 5      # Timeout for COUNT(*) per table
    max_tables_per_crawl: int = 500     # Safety cap

    @property
    def postgres_url(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
