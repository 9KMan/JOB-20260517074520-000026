from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    app_name: str = "AI Orchestration Platform"
    debug: bool = False

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_platform"
    redis_url: str = "redis://localhost:6379/0"

    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    openai_api_key: str = ""
    anthropic_api_key: str = ""

    stripe_api_key: str = ""
    stripe_webhook_secret: str = ""

    pgvector_dimension: int = 1536

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()