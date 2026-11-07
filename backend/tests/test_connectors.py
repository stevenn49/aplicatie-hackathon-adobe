"""
Connector tests.

These are hermetic: they never touch the network. A separate, opt-in module
(`test_connectors_live.py`) makes real calls and is skipped unless
MARKETPULSE_LIVE_TESTS=1 is set, so the default gate stays deterministic.
"""
import pytest

from connectors.emag import EmagConnector
from connectors.base import BaseConnector


# --------------------------------------------------------------------------- #
# eMAG price parsing
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize(
    "raw,expected",
    [
        ("3.999,99 Lei", 3999.99),
        ("899,00 lei", 899.00),
        ("2 499 RON", 2499.0),
        ("2 499 Lei", 2499.0),
        ("1.234,5 Lei", 1234.5),
        ("3.999 Lei", 3999.0),
        ("1499.99", 1499.99),
        ("5999", 5999.0),
    ],
)
def test_emag_price_parsing(raw, expected):
    connector = EmagConnector()
    value, currency = connector._clean_price(raw)
    assert currency == "RON"
    assert value == pytest.approx(expected, abs=0.01)


def test_emag_price_parsing_rejects_garbage():
    connector = EmagConnector()
    value, _ = connector._clean_price("indisponibil")
    assert value is None


@pytest.mark.parametrize(
    "title,expected",
    [
        ("Telefon mobil Apple iPhone 16", "Apple"),
        ("Placa video NVIDIA GeForce RTX 5080", "NVIDIA"),
        ("Consola Sony PlayStation 5", "Sony"),
        ("Laptop Microsoft Surface Laptop 7", "Microsoft"),
        ("Casti Samsung Galaxy Buds", "Samsung"),
        ("Produs fara brand cunoscut", "Generic"),
    ],
)
def test_emag_brand_inference(title, expected):
    connector = EmagConnector()
    assert connector._infer_brand(title) == expected


def test_emag_parses_a_synthetic_catalog_page():
    html = """
    <div class="card-item">
      <a class="card-v2-title" href="/pd/produs-test">Telefon mobil Apple iPhone 16 128GB</a>
      <p class="product-new-price">4.499,99 Lei</p>
      <div class="star-rating-container">4.7 (24)</div>
    </div>
    """
    connector = EmagConnector()
    items = connector._parse_catalog_html(html, limit=5)
    assert len(items) == 1
    assert items[0]["brand"] == "Apple"
    assert items[0]["price"] == pytest.approx(4499.99)
    assert items[0]["rating"] == pytest.approx(4.7)
    assert items[0]["review_count"] == 24
    assert items[0]["source_url"].startswith("https://www.emag.ro/")


def test_emag_ignores_cards_without_price():
    html = """
    <div class="card-item">
      <a class="card-v2-title" href="/pd/x">Produs fara pret</a>
    </div>
    """
    connector = EmagConnector()
    assert connector._parse_catalog_html(html, limit=5) == []


# --------------------------------------------------------------------------- #
# Base connector
# --------------------------------------------------------------------------- #

def test_base_connector_is_abstract():
    with pytest.raises(TypeError):
        BaseConnector(name="test")  # type: ignore[abstract]


def test_rate_limit_delay_is_enforced():
    import time

    connector = EmagConnector()
    connector.rate_limit_delay = 0.05
    connector.last_request_time = 0.0
    start = time.monotonic()
    connector._apply_rate_limit()
    connector._apply_rate_limit()
    elapsed = time.monotonic() - start
    assert elapsed >= 0.04, "the second call did not wait for the rate limit"


# --------------------------------------------------------------------------- #
# Review cleaning
# --------------------------------------------------------------------------- #

def test_review_cleaner_strips_html_and_urls():
    from data_collection.reviews import review_collector

    cleaned = review_collector.clean_text("<p>Great phone</p> see https://example.com   now")
    assert "<p>" not in cleaned
    assert "https://" not in cleaned
    assert "Great phone" in cleaned
    assert "  " not in cleaned


def test_review_search_query_simplification():
    from data_collection.reviews import review_collector

    simplified = review_collector._simplify_search_query(
        "Telefon mobil Apple iPhone 15 128GB Dual SIM Black", "Apple"
    )
    assert "Telefon mobil" not in simplified
    assert "128GB" not in simplified
    assert "iPhone" in simplified
