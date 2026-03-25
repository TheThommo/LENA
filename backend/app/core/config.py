"""
LENA Configuration
Loads environment variables and provides app-wide settings.
"""

from pydantic_settings import BaseSettings
from typing import Optional


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

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Ignore extra fields like GITHUB_PAT


settings = Settings()
