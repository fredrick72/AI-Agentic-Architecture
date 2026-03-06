from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: str
    schema_service_url: str = "http://localhost:8010"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "dbintel"
    postgres_user: str = "postgres"
    postgres_password: str = "dbintel_password"
    redis_url: str = "redis://localhost:6379"
    log_level: str = "INFO"
    max_result_rows: int = 1000
    query_timeout_seconds: int = 30

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
