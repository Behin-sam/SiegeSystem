"""
Application config with additional JWT/MFA settings for auth & identity module.
"""
from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ---- Application ----
    APP_NAME: str = "Autonomous Multi-Region Payment & Identity Settlement Network"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # ---- Security ----
    SECRET_KEY: str = "change-me"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 days

    # ---- MFA (mock) ----
    MFA_OTP_CODE: str = "123456"  # fixed mock code for all users in development

    # ---- Email Verification (mock) ----
    EMAIL_VERIFICATION_CODE: str = "verify-123"

    # ---- Database ----
    POSTGRES_USER: str = "apmisn_user"
    POSTGRES_PASSWORD: str = "apmisn_password"
    POSTGRES_DB: str = "apmisn_db"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    DATABASE_URL: str = ""

    # ---- Redis ----
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_URL: str = ""

    # ---- CORS ----
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    # ---- Logging ----
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v):
        if isinstance(v, str) and not v.startswith("["):
            return [origin.strip() for origin in v.split(",")]
        return v

    @field_validator("DATABASE_URL", mode="after")
    @classmethod
    def assemble_db_url(cls, v: str, info) -> str:
        if v:
            return v
        data = info.data
        return (
            f"postgresql+asyncpg://{data.get('POSTGRES_USER')}:"
            f"{data.get('POSTGRES_PASSWORD')}@{data.get('POSTGRES_HOST')}:"
            f"{data.get('POSTGRES_PORT')}/{data.get('POSTGRES_DB')}"
        )

    @field_validator("REDIS_URL", mode="after")
    @classmethod
    def assemble_redis_url(cls, v: str, info) -> str:
        if v:
            return v
        data = info.data
        return f"redis://{data.get('REDIS_HOST')}:{data.get('REDIS_PORT')}/{data.get('REDIS_DB')}"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
