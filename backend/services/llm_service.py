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
        self.max_tokens = settings.OPENROUTER_MAX_TOKENS

    # ------------------------------------------------------------------ #
    # Model capabilities
    # ------------------------------------------------------------------ #

    def model_limits(self, model: Optional[str] = None) -> Dict[str, Any]:
        """
        Reads the model's output budget from the public catalogue.

        OpenRouter publishes `top_provider.max_completion_tokens` and the
        supported parameters per model. Asking for more than a model allows is
        rejected, and reasoning models need most of their budget to think, so
        the request is sized from this metadata rather than from a fixed number.

        Returns {} when the catalogue is unreachable; the caller then falls back
        to the configured value.
        """
        model = model or self.model
        if not model:
            return {}

        try:
            with httpx.Client(timeout=20) as client:
                response = client.get(
                    f"{self.base_url}/models",
                    headers={"Accept": "application/json"},
                )
            if response.status_code != 200:
                return {}
            catalogue = response.json().get("data") or []
        except Exception as exc:
            logger.debug(f"Could not read the model catalogue: {exc}")
            return {}

        for entry in catalogue:
            if entry.get("id") != model:
                continue

            top_provider = entry.get("top_provider") or {}
            supported = entry.get("supported_parameters") or []
            reasoning = entry.get("reasoning") or {}

            return {
                "max_completion_tokens": top_provider.get("max_completion_tokens"),
                "context_length": entry.get("context_length"),
                "supports_reasoning": "reasoning" in supported or "include_reasoning" in supported,
                "reasoning_mandatory": bool(reasoning.get("mandatory")),
                "supports_response_format": "response_format" in supported,
            }

        return {}

    def _budget(self, requested: Optional[int]) -> int:
        """
        The token budget to send: the caller's value, capped by what the model
        reports it accepts. Never raises the requested value.
        """
        budget = requested or self.max_tokens
        limits = self.model_limits()
        ceiling = limits.get("max_completion_tokens")
        if ceiling:
            budget = min(budget, int(ceiling))
        return budget

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
        cache_only: bool = False,
    ) -> Optional[str]:
        """
        Returns the model's text, or None when the LLM is disabled or the call
        fails. Never raises.

        With `cache_only=True` it returns the cached answer or None without
        calling the model. A reasoning model takes 15-100 seconds, which is far
        too long to hold an HTTP request open, so the endpoints read the cache
        and schedule the generation in the background.
        """
        if not self.enabled:
            return None

        key = self._key(self.model, prompt)
        cached = self._cache_get(db, key)
        if cached is not None:
            logger.debug("LLM cache hit")
            return cached

        if cache_only:
            return None

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        budget = self._budget(max_tokens)
        limits = self.model_limits()

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": budget,
        }
        # Reasoning models (dots-3-note-preview, the Nemotron free models) spend
        # most of the budget thinking. Ask OpenRouter for a high reasoning effort
        # when the model advertises support, so the answer is not cut short.
        if limits.get("supports_reasoning"):
            payload["reasoning"] = {"effort": settings.OPENROUTER_REASONING_EFFORT}
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

            choice = choices[0]
            content = ((choice.get("message") or {}).get("content") or "").strip()

            if not content:
                # Reasoning models can burn the whole budget thinking and return
                # an empty content field. Say which case it was, because the fix
                # is different: raise OPENROUTER_MAX_TOKENS, or pick a model that
                # is not a reasoning model.
                finish = choice.get("finish_reason")
                usage = data.get("usage") or {}
                reasoning = (usage.get("completion_tokens_details") or {}).get("reasoning_tokens")
                if finish == "length":
                    logger.warning(
                        f"OpenRouter returned an empty answer because the token budget ran out "
                        f"(finish_reason=length, reasoning_tokens={reasoning}). "
                        f"Raise OPENROUTER_MAX_TOKENS (currently {settings.OPENROUTER_MAX_TOKENS}) "
                        f"or choose a model that is not a reasoning model."
                    )
                else:
                    logger.warning(f"OpenRouter returned an empty answer (finish_reason={finish})")
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

    def review_summary_prompt(self, product_name: str, brand: str, stats: Dict[str, Any]) -> str:
        return (
            f"Product: {product_name} by {brand}.\n"
            f"Reviews analysed: {stats.get('total_reviews', 0)}.\n"
            f"Sentiment: {stats.get('positive', 0)}% positive, "
            f"{stats.get('neutral', 0)}% neutral, {stats.get('negative', 0)}% negative.\n"
            f"Aspect scores (0-100): {json.dumps(stats.get('aspects', {}), ensure_ascii=False)}.\n\n"
            "Write exactly two sentences in English summarising what customers praise and "
            "what they criticise. Use only the numbers above. Do not invent features, prices "
            "or comparisons. Do not use bullet points."
        )

    def review_summary(self, product_name: str, brand: str, stats: Dict[str, Any], db: Optional[Session], cache_only: bool = False) -> Optional[str]:
        """Two-sentence summary of what reviewers say about one product."""
        if not self.enabled:
            return None
        return self.complete(
            self.review_summary_prompt(product_name, brand, stats),
            db=db,
            system="You are a concise market analyst.",
            cache_only=cache_only,
        )

    def executive_summary_prompt(self, payload: Dict[str, Any]) -> str:
        return (
            "Market data for a consumer-tech intelligence dashboard:\n"
            f"{json.dumps(payload, ensure_ascii=False, indent=2)}\n\n"
            "Write a JSON object with exactly two keys: \"headline\" (max 12 words) and "
            "\"body\" (3 sentences, max 90 words). Base every claim on the numbers above. "
            "Do not invent products, prices or trends. Return JSON only."
        )

    def executive_summary(self, payload: Dict[str, Any], db: Optional[Session], cache_only: bool = False) -> Optional[str]:
        """Headline + paragraph for the AI Recommendations page."""
        if not self.enabled:
            return None
        return self.complete(
            self.executive_summary_prompt(payload),
            db=db,
            system="You are a market strategy analyst. Reply with JSON only.",
            cache_only=cache_only,
        )

    def marketing_opportunities_prompt(self, payload: Dict[str, Any]) -> str:
        return (
            "Market data:\n"
            f"{json.dumps(payload, ensure_ascii=False, indent=2)}\n\n"
            "Return a JSON array of exactly three objects with keys: title (max 8 words), "
            "type (one of CONTENT OPPORTUNITY, AUDIENCE OPPORTUNITY, NARRATIVE OPPORTUNITY), "
            "detail (one sentence, max 30 words), impact (max 3 words). "
            "Ground each one in the numbers above. Return JSON only."
        )

    def marketing_opportunities(self, payload: Dict[str, Any], db: Optional[Session], cache_only: bool = False) -> Optional[str]:
        """Three opportunities as JSON, grounded in the supplied numbers."""
        if not self.enabled:
            return None
        return self.complete(
            self.marketing_opportunities_prompt(payload),
            db=db,
            system="You are a marketing strategist. Reply with JSON only.",
            cache_only=cache_only,
        )


llm_service = LLMService()


def extract_json(text: Optional[str]) -> Optional[Any]:
    """
    Pulls a JSON value out of a model's reply.

    Models wrap JSON in code fences, prepend a sentence, or append a closing
    remark. This finds the outermost object or array and parses that, so a
    correct answer is not thrown away because of surrounding prose.
    """
    if not text:
        return None

    cleaned = text.strip()

    # Strip a fenced block if there is one.
    if cleaned.startswith("```"):
        parts = cleaned.split("```")
        if len(parts) >= 2:
            cleaned = parts[1]
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:]
    cleaned = cleaned.strip()

    # Try the OUTERMOST structure first: whichever of { or [ appears earlier in
    # the text. Trying { first would pull the inner object out of a top-level
    # array and silently change the shape.
    object_start = cleaned.find("{")
    array_start = cleaned.find("[")

    candidates = []
    if array_start != -1 and (object_start == -1 or array_start < object_start):
        candidates.append(("[", "]"))
        candidates.append(("{", "}"))
    else:
        candidates.append(("{", "}"))
        candidates.append(("[", "]"))

    for opener, closer in candidates:
        start = cleaned.find(opener)
        end = cleaned.rfind(closer)
        if start != -1 and end > start:
            try:
                return json.loads(cleaned[start:end + 1])
            except Exception:
                continue
    return None
