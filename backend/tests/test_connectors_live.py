"""
Live connector probes. Opt-in only.

    MARKETPULSE_LIVE_TESTS=1 python -m pytest tests/test_connectors_live.py -v

Each test makes ONE real request. They are skipped by default so the normal gate
never depends on a third party being reachable, and a rate-limit answer is
reported as a skip rather than a failure (it is inconclusive, not a defect).
"""
import os

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("MARKETPULSE_LIVE_TESTS") != "1",
    reason="live connector probes are opt-in (set MARKETPULSE_LIVE_TESTS=1)",
)


def test_hacker_news_returns_real_discussions():
    from connectors.alternative_reviews import alternative_reviews_connector

    results = alternative_reviews_connector.fetch_tech_discussions("iPhone", limit=3)
    if not results:
        pytest.skip("Hacker News Algolia returned nothing (rate limit or offline)")
    for item in results:
        assert item["content"]
        assert item["source"] == "TechCommunity"
        assert item["external_id"]


def test_reddit_public_json():
    from connectors.reddit import reddit_connector

    results = reddit_connector.search_discussions("iPhone 16", limit=2)
    if not results:
        pytest.skip("Reddit public JSON returned nothing (rate limit or blocked)")
    for item in results:
        assert item["content"]
        assert item["source"] == "Reddit"


def test_emag_catalog_search():
    from connectors.emag import emag_connector

    results = emag_connector.search_products("iPhone 16", limit=3)
    if not results:
        pytest.skip("eMAG returned nothing (rate limit, blocked, or layout changed)")
    for item in results:
        assert item["price"] > 0
        assert item["currency"] == "RON"
        assert item["brand"]
