"""
config.py — pydantic-settings configuration.
All secrets are loaded from environment variables / .env file.
Key values are NEVER logged or exposed in responses.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Provider API keys (loaded from .env, never logged) ──────────────────
    fal_key: str
    replicate_api_token: str
    groq_api_key: str

    # ── Model IDs ────────────────────────────────────────────────────────────
    fal_image_model: str = "fal-ai/flux/dev"
    replicate_video_model: str = "luma/dream-machine"
    groq_model: str = "qwen/qwen3.6-27b"

    # ── Mocking (Development mode) ───────────────────────────────────────────
    mock_apis: bool = True

    # ── Timeouts (seconds) ───────────────────────────────────────────────────
    fal_timeout: int = 30
    replicate_timeout: int = 360      # video generation can take 2-5 min
    groq_timeout: int = 10

    # ── Retry ────────────────────────────────────────────────────────────────
    max_retry_attempts: int = 2
    retry_backoff_base: float = 1.5

    # ── Rate limiting ─────────────────────────────────────────────────────────
    rate_limit_requests: int = 10     # per IP
    rate_limit_window_seconds: int = 60

    # ── CORS ─────────────────────────────────────────────────────────────────
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
