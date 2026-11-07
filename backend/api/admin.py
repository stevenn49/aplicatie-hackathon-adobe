"""
Local administration endpoints.

These exist so the settings manager can change an API key while the server is
running, without a restart. They are deliberately narrow and local-only:

  - every route requires the request to come from the loopback interface;
  - only settings are reloaded, never the database engine, so an in-flight
    request is never interrupted;
  - nothing here writes files or reveals a secret.
"""
import logging

from fastapi import APIRouter, HTTPException, Request, status

from config import reload_settings, settings
from services.llm_service import llm_service

logger = logging.getLogger("marketpulse.api.admin")

router = APIRouter(
    prefix="/api/admin",
    tags=["Admin"]
)

LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost", "testclient"}


def _require_loopback(request: Request) -> None:
    client = request.client
    host = client.host if client else None
    if host not in LOOPBACK_HOSTS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administration endpoints are only available from this machine.",
        )


@router.post("/reload")
def reload_configuration(request: Request):
    """
    Re-read backend/.env and apply it to the running process.

    What changes immediately:
      - the OpenRouter key and model (the LLM service is rebuilt);
      - the connector credentials (X/Twitter, Reddit user agent);
      - CORS origins, for requests that arrive after this call.

    What does not change: DATABASE_URL. The engine is created at import time and
    swapping it under live connections is not safe, so a database change still
    needs a restart. The response says so explicitly.
    """
    _require_loopback(request)

    previous_model = settings.OPENROUTER_MODEL
    previous_llm = settings.llm_enabled

    reload_settings()
    llm_service.refresh()

    changed = []
    if previous_model != settings.OPENROUTER_MODEL:
        changed.append(f"OPENROUTER_MODEL: {previous_model or '(none)'} -> {settings.OPENROUTER_MODEL or '(none)'}")
    if previous_llm != settings.llm_enabled:
        changed.append(f"llm_enabled: {previous_llm} -> {settings.llm_enabled}")

    logger.info(f"Configuration reloaded; {len(changed)} change(s): {changed}")

    return {
        "status": "reloaded",
        "llm": "configured" if settings.llm_enabled else "not configured",
        "llm_model": settings.OPENROUTER_MODEL or None,
        "twitter": "configured" if settings.TWITTER_BEARER_TOKEN.strip() else "not configured",
        "changes": changed,
        "restart_required_for": ["DATABASE_URL", "PORT", "HOST"],
    }


@router.get("/config")
def read_configuration(request: Request):
    """
    The non-secret part of the current configuration, for the settings manager
    to confirm what the running process actually holds.
    """
    _require_loopback(request)

    return {
        "llm": "configured" if settings.llm_enabled else "not configured",
        "llm_model": settings.OPENROUTER_MODEL or None,
        "llm_base_url": settings.OPENROUTER_BASE_URL,
        "twitter": "configured" if settings.TWITTER_BEARER_TOKEN.strip() else "not configured",
        "reddit_user_agent": settings.REDDIT_USER_AGENT,
        "database_backend": settings.DATABASE_URL.split("://")[0],
        "cors_origins": settings.cors_origins,
        "environment": settings.APP_ENV,
    }
