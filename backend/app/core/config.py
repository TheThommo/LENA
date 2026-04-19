"""
LENA Configuration
Loads environment variables and provides app-wide settings.
"""

from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import Optional
import os


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
    app_port: int = int(os.getenv("PORT", 8000))
    cors_origins: str = "http://localhost:3000,https://lena-app.up.railway.app"
    railway_environment: Optional[str] = None

    # OpenAI
    openai_api_key: Optional[str] = None

    # Supabase
    supabase_url: Optional[str] = None
    supabase_anon_key: Optional[str] = None
    supabase_service_role_key: Optional[str] = None

    # NCBI / PubMed
    ncbi_api_key: Optional[str] = None
    ncbi_email: Optional[str] = None

    # Authentication & JWT
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 480  # 8 hours (admin tokens live 8h, not 24h)

    # Freemium
    # Anonymous visitors get 1 free search before signup CTA (demo mode).
    # Registered users get 5 per rolling 24h before Pro gate (demo mode).
    # Tighten both when billing goes live.
    free_search_limit: int = 5  # legacy alias; kept for backward-compat readers
    free_search_limit_anon: int = 1
    free_search_limit_registered: int = 5
    anon_fingerprint_salt: str = "lena-fp-demo-salt-rotate-before-prod"

    # Email (Resend)
    resend_api_key: Optional[str] = None
    admin_email: str = "mark.e.s.thompson@gmail.com"
    support_email: str = "hello@lena-app.com"
    app_url: str = "https://lena-app.up.railway.app"

    # Stripe (billing).
    # Set STRIPE_SECRET_KEY + STRIPE_WEBHOOK_SECRET in Railway prod env.
    # Price IDs come from the Stripe dashboard after products are created.
    # Founding-50 redemption is tracked by counting active subscriptions on
    # the founding price in tenant_subscriptions (see billing.py).
    stripe_secret_key: Optional[str] = None
    stripe_publishable_key: Optional[str] = None
    stripe_webhook_secret: Optional[str] = None
    stripe_price_pro_monthly: Optional[str] = None
    stripe_price_pro_annual: Optional[str] = None
    stripe_price_pro_founding: Optional[str] = None
    stripe_founding_max_redemptions: int = 10
    billing_success_url: str = "https://lena-app.up.railway.app/?billing=success"
    billing_cancel_url: str = "https://lena-app.up.railway.app/?billing=cancelled"

    # Rate limiting
    rate_limit_per_minute: int = 60

    @field_validator(
        "openai_api_key", "supabase_url", "supabase_anon_key",
        "supabase_service_role_key", "ncbi_api_key", "ncbi_email", "resend_api_key",
        "stripe_secret_key", "stripe_publishable_key", "stripe_webhook_secret",
        "stripe_price_pro_monthly", "stripe_price_pro_annual", "stripe_price_pro_founding",
        mode="before",
    )
    @classmethod
    def strip_placeholders(cls, v):
        return _clean_placeholder(v)

    @property
    def stripe_enabled(self) -> bool:
        """True when the Stripe secret + at least one price ID are present."""
        return bool(
            self.stripe_secret_key
            and (
                self.stripe_price_pro_monthly
                or self.stripe_price_pro_annual
                or self.stripe_price_pro_founding
            )
        )

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.app_env.lower() == "production"

    @property
    def on_railway(self) -> bool:
        """Check if running on Railway infrastructure."""
        return os.getenv("RAILWAY_ENVIRONMENT") is not None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Ignore extra fields like GITHUB_PAT


settings = Settings()
