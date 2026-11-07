"""
OpenRouter LLM client.

Used for the three surfaces where a language model adds real value:
  - the AI Recommendations executive summary and per-item rationale
  - the product review summary in the drawer
  - the marketing opportunities narrative

Everything else (sentiment, price maths, segments) stays deterministic and local.

Design rules:
  - No key or no model configured -> `available` is False and every call returns
    None. The caller then uses its derived text and labels the source honestly.
  - Every response is cached in `llm_cache` keyed by a hash of (model, prompt),
    because the free tier allows roughly 1000 requests per day.
  - A failure never raises into the request path: it logs and returns None.
"""
import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import httpx
from sqlalchemy.orm import Session

from config import settings
from database.models import LLMCache

logger = logging.getLogger("marketpulse.services.llm")

CACHE_TTL_HOURS = 12


class LLMService:
    def __init__(self) -> None:
        self._read_settings()
        if not self.enabled:
            logger.info(
                "OpenRouter is not configured (OPENROUTER_API_KEY / OPENROUTER_MODEL empty). "
                "LLM surfaces will use the derived engine and say so."
            )

    def _read_settings(self) -> None:
        """Copies the live settings into the instance fields."""
        self.enabled = settings.llm_enabled
        self.model = settings.OPENROUTER_MODEL
        self.base_url = settings.OPENROUTER_BASE_URL.rstrip("/")

    def refresh(self) -> None:
        """
        Re-reads the settings after `reload_settings()` changed them, so a key
        written to .env applies without restarting the process.
        """
        was_enabled = self.enabled
        self._read_settings()
        if was_enabled != self.enabled:
            logger.info(
                f"LLM service {'enabled' if self.enabled else 'disabled'} after a configuration reload."
            )

    # ------------------------------------------------------------------ #
    # Cache
    # ------------------------------------------------------------------ #

    @staticmethod
    def _key(model: str, prompt: str) -> str:
        return hashlib.sha256(f"{model}\n{prompt}".encode("utf-8")).hexdigest()

    def _cache_get(self, db: Optional[Session], key: str) -> Optional[str]:
        if db is None:
            return None
        row = db.query(LLMCache).filter(LLMCache.cache_key == key).first()
        if not row:
            return None
        if row.expires_at and row.expires_at < datetime.utcnow():
            return None
        return row.response

    def _cache_put(self, db: Optional[Session], key: str, prompt: str, response: str) -> None:
        if db is None:
            return
        try:
            existing = db.query(LLMCache).filter(LLMCache.cache_key == key).first()
            if existing:
                existing.response = response
                existing.created_at = datetime.utcnow()
                existing.expires_at = datetime.utcnow() + timedelta(hours=CACHE_TTL_HOURS)
            else:
                db.add(LLMCache(
                    cache_key=key,
                    model=self.model,
                    prompt=prompt,
                    response=response,
                    expires_at=datetime.utcnow() + timedelta(hours=CACHE_TTL_HOURS),
                ))
            db.commit()
        except Exception as exc:
            logger.warning(f"Could not write the LLM cache: {exc}")
            db.rollback()

    # ------------------------------------------------------------------ #
    # Completion
    # ------------------------------------------------------------------ #

    def complete(
        self,
        prompt: str,
        db: Optional[Session] = None,
        system: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
    ) -> Optional[str]:
        """
        Returns the model's text, or None when the LLM is disabled or the call
        fails. Never raises.
        """
        if not self.enabled:
            return None

        key = self._key(self.model, prompt)
        cached = self._cache_get(db, key)
        if cached is not None:
            logger.debug("LLM cache hit")
            return cached

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens or settings.OPENROUTER_MAX_TOKENS,
        }
        headers = {
            "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": settings.OPENROUTER_APP_URL,
            "X-Title": settings.OPENROUTER_APP_NAME,
        }

        url = f"{self.base_url}/chat/completions"
        try:
            with httpx.Client(timeout=settings.OPENROUTER_TIMEOUT) as client:
                response = client.post(url, json=payload, headers=headers)
            if response.status_code != 200:
                logger.warning(
                    f"OpenRouter returned {response.status_code}: {response.text[:300]}"
                )
                return None
            data = response.json()
            choices = data.get("choices") or []
            if not choices:
                logger.warning("OpenRouter returned no choices")
                return None
            content = (choices[0].get("message") or {}).get("content") or ""
            content = content.strip()
            if not content:
                return None
            self._cache_put(db, key, prompt, content)
            return content
        except httpx.RequestError as exc:
            logger.warning(f"OpenRouter request failed: {exc}")
            return None
        except Exception as exc:
            logger.warning(f"OpenRouter unexpected error: {exc}")
            return None

    # ------------------------------------------------------------------ #
    # Prompt builders
    # ------------------------------------------------------------------ #

    def review_summary(self, product_name: str, brand: str, stats: Dict[str, Any], db: Optional[Session]) -> Optional[str]:
        """Two-sentence summary of what reviewers say about one product."""
        if not self.enabled:
            return None
        prompt = (
            f"Product: {product_name} by {brand}.\n"
            f"Reviews analysed: {stats.get('total_reviews', 0)}.\n"
            f"Sentiment: {stats.get('positive', 0)}% positive, "
            f"{stats.get('neutral', 0)}% neutral, {stats.get('negative', 0)}% negative.\n"
            f"Aspect scores (0-100): {json.dumps(stats.get('aspects', {}), ensure_ascii=False)}.\n\n"
            "Write exactly two sentences in English summarising what customers praise and "
            "what they criticise. Use only the numbers above. Do not invent features, prices "
            "or comparisons. Do not use bullet points."
        )
        return self.complete(prompt, db=db, system="You are a concise market analyst.")

    def executive_summary(self, payload: Dict[str, Any], db: Optional[Session]) -> Optional[str]:
        """Headline + paragraph for the AI Recommendations page."""
        if not self.enabled:
            return None
        prompt = (
            "Market data for a consumer-tech intelligence dashboard:\n"
            f"{json.dumps(payload, ensure_ascii=False, indent=2)}\n\n"
            "Write a JSON object with exactly two keys: \"headline\" (max 12 words) and "
            "\"body\" (3 sentences, max 90 words). Base every claim on the numbers above. "
            "Do not invent products, prices or trends. Return JSON only."
        )
        return self.complete(prompt, db=db, system="You are a market strategy analyst. Reply with JSON only.")

    def marketing_opportunities(self, payload: Dict[str, Any], db: Optional[Session]) -> Optional[str]:
        """Three opportunities as JSON, grounded in the supplied numbers."""
        if not self.enabled:
            return None
        prompt = (
            "Market data:\n"
            f"{json.dumps(payload, ensure_ascii=False, indent=2)}\n\n"
            "Return a JSON array of exactly three objects with keys: title (max 8 words), "
            "type (one of CONTENT OPPORTUNITY, AUDIENCE OPPORTUNITY, NARRATIVE OPPORTUNITY), "
            "detail (one sentence, max 30 words), impact (max 3 words). "
            "Ground each one in the numbers above. Return JSON only."
        )
        return self.complete(prompt, db=db, system="You are a marketing strategist. Reply with JSON only.")


llm_service = LLMService()
