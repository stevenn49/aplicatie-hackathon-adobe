import os
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """
    Application Settings loaded from environment variables or .env file.

    The database is MySQL. Two supported setups, both driven by DATABASE_URL:
      - Docker (default):  mysql+pymysql://marketpulse:marketpulse@127.0.0.1:3307/marketpulse
      - Native install:    mysql+pymysql://marketpulse:marketpulse@127.0.0.1:3306/marketpulse
    Point DATABASE_URL at whichever one is running; nothing else changes.
    """
    APP_NAME: str = "MarketPulse AI Backend"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_PREFIX: str = "/api"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # CORS settings - split comma separated string into list
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173"

    # Database. MySQL only. There is no SQLite fallback: a wrong URL must fail loudly.
    DATABASE_URL: str = "mysql+pymysql://marketpulse:marketpulse@127.0.0.1:3307/marketpulse"
    DB_POOL_SIZE: int = 10
    DB_POOL_RECYCLE: int = 1800

    # External Connectors Configuration
    EMAG_REQUEST_TIMEOUT: int = 15
    EMAG_USER_AGENT: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
    EMAG_RATE_LIMIT_DELAY: float = 1.5

    # Reddit API Credentials (optional, public JSON endpoints used as fallback)
    REDDIT_CLIENT_ID: str = ""
    REDDIT_CLIENT_SECRET: str = ""
    REDDIT_USER_AGENT: str = "MarketPulseAI/1.0"

    # Twitter / X API Credentials
    TWITTER_BEARER_TOKEN: str = ""

    # OpenRouter LLM. Empty key = the LLM surfaces degrade to the rule-based engine
    # and say so; nothing is fabricated.
    OPENROUTER_API_KEY: str = ""
    # Free model used when the key is present and no model was chosen explicitly.
    # dots-3-note-preview has a 512k-token context, costs nothing, and is not region-locked.
    OPENROUTER_MODEL: str = "dots-studio/dots-3-note-preview:free"
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_TIMEOUT: int = 300
    # Output budget. Reasoning models spend most of it thinking before they emit
    # any content: dots-3-note-preview used ~5,300 reasoning tokens before the
    # JSON summary, and 900 came back empty with finish_reason=length.
    #
    # The service caps this against the model's own `max_completion_tokens` from
    # /api/v1/models, so a model that allows less is never over-asked. 64k is the
    # default because the configured model allows 460,800.
    OPENROUTER_MAX_TOKENS: int = 65536
    # Sent as `reasoning.effort` for models that advertise the `reasoning`
    # parameter. "high" gives a reasoning model room to plan before answering.
    OPENROUTER_REASONING_EFFORT: str = "high"
    OPENROUTER_APP_NAME: str = "MarketPulse AI"
    OPENROUTER_APP_URL: str = "http://localhost:5173"

    # The in-app assistant (backend/server.py) reuses the OpenRouter key and
    # model by default, so one key covers every AI surface.
    AI_PROVIDER: str = "openrouter"
    GROQ_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    OLLAMA_URL: str = "http://localhost:11434"

    @property
    def cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

    @property
    def llm_enabled(self) -> bool:
        return bool(self.OPENROUTER_API_KEY.strip() and self.OPENROUTER_MODEL.strip())

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()


def reload_settings() -> "Settings":
    """
    Re-reads backend/.env and updates the live `settings` object in place.

    The API keeps one Settings instance for the whole process, so a key written
    to .env while the server is running would otherwise only take effect after a
    restart. Updating the fields in place lets the admin endpoint apply a change
    without dropping the database connections.

    Returns the same object, refreshed.
    """
    fresh = Settings()
    for field_name in fresh.model_fields:
        try:
            setattr(settings, field_name, getattr(fresh, field_name))
        except Exception:
            # A read-only or computed field is skipped rather than failing the reload.
            continue
    return settings
