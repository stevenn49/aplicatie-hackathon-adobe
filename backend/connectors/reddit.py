import time
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta

from connectors.base import BaseConnector
from config import settings

logger = logging.getLogger("marketpulse.connectors.reddit")

OAUTH_TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
OAUTH_API_BASE = "https://oauth.reddit.com"
PUBLIC_API_BASE = "https://www.reddit.com"


class RedditConnector(BaseConnector):
    """
    Reddit Discussions & Sentiment Connector.

    Access, as of 2026:
      - Reddit requires OAuth for the Data API. The free tier allows 100 queries
        per minute per OAuth client id and is limited to non-commercial use.
      - The public `.json` endpoints started returning 403 to unauthenticated
        traffic around May 2026, and datacenter IPs are blocked first. They are
        kept here only as a last-resort fallback, and a failure is reported as
        "unavailable" rather than silently returning nothing.

    Set REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET to use OAuth. Without them the
    connector still tries the public endpoints and says so when they fail.
    """

    def __init__(self):
        super().__init__(name="Reddit", rate_limit_delay=2.0, timeout=15)
        self.headers = {
            "User-Agent": settings.REDDIT_USER_AGENT or "MarketPulseAI/1.0 (by /u/marketpulse)"
        }
        self.subreddits = ["technology", "gadgets", "hardware", "apple", "android", "Romania"]
        self._token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
        self.last_status = "unknown"

    # ------------------------------------------------------------------ #
    # Authentication
    # ------------------------------------------------------------------ #

    @property
    def oauth_configured(self) -> bool:
        return bool(settings.REDDIT_CLIENT_ID.strip() and settings.REDDIT_CLIENT_SECRET.strip())

    def _get_token(self) -> Optional[str]:
        """
        Client-credentials OAuth token, cached until shortly before it expires.
        Returns None when OAuth is not configured or the token request fails.
        """
        if not self.oauth_configured:
            return None

        if self._token and self._token_expires_at and datetime.utcnow() < self._token_expires_at:
            return self._token

        try:
            with self.fetch_client() as client:
                response = client.post(
                    OAUTH_TOKEN_URL,
                    auth=(settings.REDDIT_CLIENT_ID, settings.REDDIT_CLIENT_SECRET),
                    data={"grant_type": "client_credentials"},
                    headers={"User-Agent": self.headers["User-Agent"]},
                )
            if response.status_code != 200:
                logger.warning(f"[Reddit] OAuth token request failed: HTTP {response.status_code}")
                self.last_status = "oauth_rejected"
                return None

            payload = response.json()
            token = payload.get("access_token")
            if not token:
                logger.warning("[Reddit] OAuth response contained no access_token")
                self.last_status = "oauth_rejected"
                return None

            expires_in = int(payload.get("expires_in", 3600))
            self._token = token
            # Refresh a minute early so a request never races the expiry.
            self._token_expires_at = datetime.utcnow() + timedelta(seconds=max(60, expires_in - 60))
            logger.info("[Reddit] OAuth token acquired")
            return self._token
        except Exception as exc:
            logger.warning(f"[Reddit] OAuth token request errored: {exc}")
            self.last_status = "oauth_error"
            return None

    def fetch_client(self):
        """An httpx client, isolated so tests can substitute it."""
        import httpx
        return httpx.Client(timeout=self.timeout, follow_redirects=True)

    # ------------------------------------------------------------------ #
    # Search
    # ------------------------------------------------------------------ #

    def search_products(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Searches Reddit posts discussing the given product or brand.
        """
        return self.search_discussions(query, limit=limit)

    def search_discussions(self, query: str, subreddit: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Searches posts discussing a product or tech topic.

        Tries the authenticated endpoint first, then the public one. Returns an
        empty list when neither works, and records why in `last_status`.
        """
        token = self._get_token()

        if token:
            items = self._search_authenticated(query, subreddit, limit, token)
            if items is not None:
                self.last_status = "ok_oauth"
                return items

        items = self._search_public(query, subreddit, limit)
        if items is not None:
            self.last_status = "ok_public"
            return items

        self.last_status = self.last_status if self.last_status != "unknown" else "unavailable"
        logger.warning(
            f"[Reddit] No data for '{query}'. Status: {self.last_status}. "
            "Reddit requires OAuth since 2026; set REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET."
        )
        return []

    def _search_authenticated(self, query: str, subreddit: Optional[str], limit: int, token: str) -> Optional[List[Dict[str, Any]]]:
        if subreddit:
            url = f"{OAUTH_API_BASE}/r/{subreddit}/search"
            params = {"q": query, "restrict_sr": "true", "sort": "relevance", "limit": str(limit), "raw_json": "1"}
        else:
            url = f"{OAUTH_API_BASE}/search"
            params = {"q": f"{query} (review OR impressions OR hands-on)", "sort": "relevance", "limit": str(limit), "raw_json": "1"}

        headers = {**self.headers, "Authorization": f"bearer {token}"}
        logger.info(f"[Reddit] Querying the authenticated API for '{query}'...")

        self._apply_rate_limit()
        try:
            with self.fetch_client() as client:
                response = client.get(url, params=params, headers=headers)
            if response.status_code == 401:
                self._token = None
                self.last_status = "oauth_rejected"
                return None
            if response.status_code != 200:
                logger.warning(f"[Reddit] Authenticated search returned HTTP {response.status_code}")
                return None
            return self._parse_listing(response.json())
        except Exception as exc:
            logger.warning(f"[Reddit] Authenticated search errored: {exc}")
            return None

    def _search_public(self, query: str, subreddit: Optional[str], limit: int) -> Optional[List[Dict[str, Any]]]:
        if subreddit:
            url = f"{PUBLIC_API_BASE}/r/{subreddit}/search.json"
            params = {"q": query, "restrict_sr": "1", "sort": "relevance", "limit": str(limit)}
        else:
            url = f"{PUBLIC_API_BASE}/search.json"
            params = {"q": f"{query} (review OR impressions OR hands-on)", "sort": "relevance", "limit": str(limit)}

        logger.info(f"[Reddit] Trying the public JSON endpoint for '{query}'...")
        response = self.fetch_get(url, params=params, headers=self.headers)
        if not response:
            return None
        try:
            return self._parse_listing(response.json())
        except Exception as exc:
            logger.warning(f"[Reddit] Could not parse the public response: {exc}")
            return None

    def _parse_listing(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        posts = payload.get("data", {}).get("children", [])
        items: List[Dict[str, Any]] = []

        for p in posts:
            data = p.get("data", {})
            title = data.get("title", "")
            selftext = data.get("selftext", "")
            content = f"{title}\n\n{selftext}".strip()

            if not content or len(content) < 15:
                continue

            upvote_ratio = data.get("upvote_ratio", 0.8)
            # Map upvote ratio (0.0 to 1.0) to a 1.0-5.0 scale
            rating = round(1.0 + (upvote_ratio * 4.0), 1)

            created_utc = data.get("created_utc")
            published_at = datetime.utcfromtimestamp(created_utc) if created_utc else None

            items.append({
                "external_id": data.get("id"),
                "author": f"u/{data.get('author', 'redditor')}",
                "title": title,
                "content": content,
                "rating": rating,
                "score": data.get("score", 0),
                "num_comments": data.get("num_comments", 0),
                "permalink": f"https://www.reddit.com{data.get('permalink', '')}",
                "published_at": published_at,
                "source": "Reddit"
            })

        logger.info(f"[Reddit] Parsed {len(items)} discussions")
        return items


reddit_connector = RedditConnector()
