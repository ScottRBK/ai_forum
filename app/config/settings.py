"""
Configuration Management for AI Forum
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from pydantic import ConfigDict

load_dotenv()

ENVIRONMENT = os.getenv("ENVIRONMENT", "example")


class Settings(BaseSettings):
    # Application Info
    SERVICE_NAME: str = "AI Forum"
    SERVICE_VERSION: str = "v1.0.0"
    SERVICE_DESCRIPTION: str = "AI-only discussion forum with reverse CAPTCHA"

    # Server Configuration
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8000
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "console"

    # Database Configuration
    DATABASE: str = "Postgres"
    DATABASE_URL: str = "postgresql+asyncpg://ai_forum:ai_forum@127.0.0.1:5432/ai_forum"
    DB_LOGGING: bool = False

    # Challenge Configuration
    CHALLENGE_EXPIRY_MINUTES: int = 10

    # Pagination Defaults
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    """Pydantic Configuration"""

    model_config = ConfigDict(
        # Only load .env file for non-production environments
        env_file=f"docker/.env.{ENVIRONMENT}" if ENVIRONMENT != "production" else None,
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Property accessors for convenience (lowercase)
    @property
    def environment(self) -> str:
        return ENVIRONMENT

    @property
    def log_level(self) -> str:
        return self.LOG_LEVEL

settings = Settings()
