"""Application settings loaded from environment variables and .env."""

from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Core
    database_url: str = "postgresql+asyncpg://forge:forge@db:5432/forge"
    redis_url: str = "redis://redis:6379/0"

    # Auth / JWT
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # SSO / SCIM — empty OIDC values mean the endpoints run in stub mode
    scim_token: str = "changeme-scim-secret"
    oidc_client_id: str = ""
    oidc_client_secret: str = ""

    # Frontend (used for invite / verification links)
    frontend_url: str = "http://localhost:5173"

    # Reports
    report_storage_dir: str = "./var/reports"

    # LLM (AI Cortex) — empty api key means the deterministic mock provider is used
    llm_base_url: str = "https://api.deepseek.com/v1"
    llm_api_key: str | None = ""
    llm_model: str = "deepseek-chat"
    # "auto" (mock when no key, openai-compatible otherwise) or "mock" to force
    llm_provider: str = "auto"
    llm_timeout_seconds: float = 60.0
    llm_max_retries: int = 3
    # Per-1k-token pricing; 0.0 means cost tracking is disabled (cost_usd -> 0.0)
    llm_cost_per_1k_input_tokens: float = 0.0
    llm_cost_per_1k_output_tokens: float = 0.0
    # Per-task model overrides — empty falls back to llm_model (model router).
    # Both MODEL_* and DEEPSEEK_MODEL_* env names are accepted (Day 32 spec).
    model_executive_summary: str = Field(
        default="",
        validation_alias=AliasChoices(
            "model_executive_summary", "MODEL_EXECUTIVE_SUMMARY", "DEEPSEEK_MODEL_EXECUTIVE_SUMMARY"
        ),
    )
    model_counterfactual: str = Field(
        default="",
        validation_alias=AliasChoices(
            "model_counterfactual", "MODEL_COUNTERFACTUAL", "DEEPSEEK_MODEL_COUNTERFACTUAL"
        ),
    )
    model_narrative: str = Field(
        default="",
        validation_alias=AliasChoices(
            "model_narrative", "MODEL_NARRATIVE", "DEEPSEEK_MODEL_NARRATIVE"
        ),
    )
    model_default: str = Field(
        default="",
        validation_alias=AliasChoices(
            "model_default", "MODEL_DEFAULT", "DEEPSEEK_MODEL_DEFAULT"
        ),
    )

    # Stripe billing
    stripe_secret_key: str | None = None
    stripe_webhook_secret: str | None = None
    stripe_price_pro_monthly: str | None = None
    stripe_price_enterprise_monthly: str | None = None

    # Email (SMTP) — empty host means the console backend is used (dev/test)
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_tls: bool = True
    emails_from: str = "The Forge <noreply@forge.app>"
    smtp_from: str = "noreply@forge.local"

    # App
    app_name: str = "The Forge"
    app_version: str = "0.1.0"
    debug: bool = False

    # Environment — "production" flips HSTS on and CORS to prod origins
    environment: str = "development"
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # Security / rate limiting (T49)
    rate_limit_default: str = "100/minute"
    rate_limit_auth: str = "10/minute"
    rate_limit_register: str = "20/minute"
    # "testing" disables the global limiter in tests (except dedicated tests).
    testing: bool = False

    # Observability (T48) — empty SENTRY_DSN disables Sentry; Prometheus /metrics
    # is always exposed.
    sentry_dsn: str = ""
    sentry_traces_sample_rate: float = 0.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
