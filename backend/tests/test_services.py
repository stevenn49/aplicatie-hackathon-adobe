"""
Unit tests for the derivation layer and the connectors that must not fabricate.
"""
import pytest

from services.analytics_service import AnalyticsService, brand_color
from services.forecasting import PriceForecastingService
from services.sentiment_analysis import SentimentAnalysisService


class FakeReview:
    """Minimal stand-in for the ORM Review, so these tests need no database."""

    def __init__(self, label, score, aspects=None, content=""):
        self.sentiment_label = label
        self.sentiment_score = score
        self.aspects = aspects or {}
        self.content = content


class FakePrice:
    def __init__(self, price):
        self.price = price


# --------------------------------------------------------------------------- #
# Sentiment
# --------------------------------------------------------------------------- #

def test_sentiment_labels_positive_and_negative():
    service = SentimentAnalysisService()
    assert service.analyze_text("This phone is excellent, the battery is amazing")["label"] == "positive"
    assert service.analyze_text("Terrible product, the battery is awful and it lags")["label"] == "negative"


def test_sentiment_handles_empty_text():
    service = SentimentAnalysisService()
    result = service.analyze_text("")
    assert result["label"] == "neutral"
    assert result["score"] == 0.0
    assert result["aspects"] == {}


def test_aspect_extraction_finds_battery_and_camera():
    service = SentimentAnalysisService()
    result = service.analyze_text("The battery lasts two days and the camera is great.")
    assert "battery" in result["aspects"]
    assert "camera" in result["aspects"]


# --------------------------------------------------------------------------- #
# Analytics derivations
# --------------------------------------------------------------------------- #

def test_product_sentiment_returns_none_without_reviews():
    service = AnalyticsService()
    assert service.product_sentiment([]) is None


def test_product_sentiment_is_bounded():
    service = AnalyticsService()
    reviews = [FakeReview("positive", 0.9) for _ in range(4)]
    score = service.product_sentiment(reviews)
    assert 0 <= score <= 100
    assert score > 80

    negative = [FakeReview("negative", -0.9) for _ in range(4)]
    assert service.product_sentiment(negative) < 30


def test_price_change_returns_none_with_one_point():
    service = AnalyticsService()
    assert service.price_change([FakePrice(100)], 100) is None


def test_price_change_uses_the_oldest_point():
    service = AnalyticsService()
    history = [FakePrice(120), FakePrice(110), FakePrice(100)]
    assert service.price_change(history, 100) == pytest.approx(-16.7, abs=0.1)


def test_price_change_positive_when_price_rose():
    service = AnalyticsService()
    history = [FakePrice(80), FakePrice(90), FakePrice(100)]
    assert service.price_change(history, 100) == pytest.approx(25.0, abs=0.1)


def test_aspect_breakdown_scores():
    service = AnalyticsService()
    reviews = [
        FakeReview("positive", 0.5, {"battery": {"sentiment": "positive"}}),
        FakeReview("positive", 0.5, {"battery": {"sentiment": "positive"}}),
        FakeReview("negative", -0.5, {"battery": {"sentiment": "negative"}}),
    ]
    breakdown = service.aspect_breakdown(reviews)
    assert breakdown["battery"]["total"] == 3
    assert breakdown["battery"]["positive"] == 2
    assert breakdown["battery"]["negative"] == 1
    # (2 positive + 0 neutral*0.5) / 3 = 66.7
    assert breakdown["battery"]["score"] == pytest.approx(66.7, abs=0.1)


def test_pros_cons_empty_without_aspects():
    service = AnalyticsService()
    pros, cons = service.pros_cons({})
    assert pros == []
    assert cons == []


def test_keyword_cloud_ignores_stopwords():
    service = AnalyticsService()
    reviews = [FakeReview("positive", 0.6, content="the battery is great and the battery is fine")]
    keywords = service.keyword_cloud(reviews)
    words = [item["word"] for item in keywords]
    assert "battery" in words
    assert "the" not in words
    assert "and" not in words


def test_brand_color_is_stable_and_known():
    assert brand_color("Apple") == "#8b8cf7"
    assert brand_color("Sony") == "#e8788c"
    # Unknown brands get a deterministic colour from the hash.
    assert brand_color("Acme") == brand_color("Acme")
    assert brand_color("Acme").startswith("#")


# --------------------------------------------------------------------------- #
# Forecasting
# --------------------------------------------------------------------------- #

def test_forecast_needs_two_points():
    service = PriceForecastingService()
    result = service.forecast_next_period([100])
    assert result["trend"] == "insufficient_data"


def test_forecast_projects_a_rising_series():
    service = PriceForecastingService()
    result = service.forecast_next_period([100, 110, 120, 130], periods_ahead=5)
    assert result["trend"] == "increasing"
    assert result["projected_price"] > 130


def test_forecast_projects_a_falling_series():
    service = PriceForecastingService()
    result = service.forecast_next_period([130, 120, 110, 100], periods_ahead=5)
    assert result["trend"] == "decreasing"
    assert result["projected_price"] < 100


def test_analyze_price_history_reports_change_from_first_point():
    service = PriceForecastingService()
    history = [FakePrice(200), FakePrice(180), FakePrice(150)]
    result = service.analyze_price_history(
        product_id=1, product_name="Test", current_price=150, price_history=history
    )
    assert result["minimum_price"] == 150
    assert result["maximum_price"] == 200
    assert result["price_change_percentage"] == pytest.approx(-25.0, abs=0.1)


# --------------------------------------------------------------------------- #
# Connectors must not fabricate
# --------------------------------------------------------------------------- #

def test_google_trends_returns_empty_when_unavailable(monkeypatch):
    """
    Regression: the connector used to return a hardcoded 88.0 / 72.0 score
    labelled as a measurement when pytrends failed.
    """
    from connectors.google_trends import GoogleTrendsConnector

    connector = GoogleTrendsConnector()
    connector._pytrends = None  # force the unavailable path
    assert connector.get_interest("some keyword") == []


# --------------------------------------------------------------------------- #
# LLM response handling
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize(
    "raw,expected",
    [
        ('{"headline": "a", "body": "b"}', {"headline": "a", "body": "b"}),
        ('```json\n{"headline": "a", "body": "b"}\n```', {"headline": "a", "body": "b"}),
        ('Here is the JSON:\n{"headline": "a", "body": "b"}\nHope it helps.', {"headline": "a", "body": "b"}),
        ('[{"title": "one"}, {"title": "two"}]', [{"title": "one"}, {"title": "two"}]),
        ("```\n[{\"title\": \"one\"}]\n```", [{"title": "one"}]),
    ],
)
def test_extract_json_handles_model_wrapping(raw, expected):
    """
    Reasoning models wrap JSON in prose or a code fence. A correct answer must
    not be discarded because of the wrapper.
    """
    from services.llm_service import extract_json

    assert extract_json(raw) == expected


@pytest.mark.parametrize("raw", ["", None, "no json here", "{broken", "```\n\n```"])
def test_extract_json_returns_none_for_junk(raw):
    from services.llm_service import extract_json

    assert extract_json(raw) is None


def test_llm_budget_is_capped_by_the_model_limit(monkeypatch):
    """
    The service reads each model's own max_completion_tokens and never asks for
    more than the model accepts.
    """
    from services.llm_service import llm_service

    monkeypatch.setattr(llm_service, "model_limits", lambda model=None: {"max_completion_tokens": 4096})
    assert llm_service._budget(65536) == 4096
    assert llm_service._budget(1000) == 1000


def test_llm_budget_falls_back_when_limits_are_unknown(monkeypatch):
    from services.llm_service import llm_service

    monkeypatch.setattr(llm_service, "model_limits", lambda model=None: {})
    assert llm_service._budget(65536) == 65536
