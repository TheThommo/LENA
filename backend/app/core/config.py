"""
LENA Configuration
Loads environment variables and provides app-wide settings.
"""

from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import Optional


# Placeholder strings that should be treated as "not set"
_PLACEHOLDER_PATTERNS = ("your-", "sk-your", "https://your-")


def _clean_placeholder(value: Optional[str]) -> Optional[str]:
    """Return None if the value looks like a placeholder from .env.example."""
    if not value or not value.strip():
        return None
    for pattern in _PLACEHOLDER_PATTERNS:
        if value.strip().startswith(pattern):
            return None
    return value.strip()


class Settings(BaseSettings):
    # App
    app_env: str = "development"
    app_debug: bool = True
    app_port: int = 8000
    cors_origins: str = "http://localhost:3000"

    # OpenAI
    openai_api_key: Optional[str] = None

    # Supabase
    supabase_url: Optional[str] = None
    supabase_anon_key: Optional[str] = None
    supabase_service_role_key: Optional[str] = None

    # NCBI / PubMed
    ncbi_api_key: Optional[str] = None
    ncbi_email: Optional[str] = None

    # Rate limiting
    rate_limit_per_minute: int = 60

    @field_validator(
        "openai_api_key", "supabase_url", "supabase_anon_key",
        "supabase_service_role_key", "ncbi_api_key", "ncbi_email",
        mode="before",
    )
    @classmethod
    def strip_placeholders(cls, v):
        return _clean_placeholder(v)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Ignore extra fields like GITHUB_PAT


settings = Settings()
