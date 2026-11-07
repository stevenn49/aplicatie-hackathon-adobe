"""
API contract tests.

These assert the shapes `src/services/api.js` consumes. A change to a response
model that breaks the dashboard must fail here first.
"""
import pytest


def test_health_reports_mysql(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "online"
    assert body["database"] == "healthy"
    assert body["database_backend"].startswith("mysql")


def test_root_lists_docs(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["documentation"] == "/docs"


def test_products_list_has_dashboard_fields(client):
    response = client.get("/api/products")
    assert response.status_code == 200
    products = response.json()
    assert len(products) >= 5

    required = {
        "id", "name", "brand", "category", "price", "currency", "rating",
        "review_count", "sentiment", "change", "interest", "color", "launch",
        "specs", "pros", "cons",
    }
    for product in products:
        missing = required - set(product)
        assert not missing, f"{product['name']} is missing {missing}"

    # Derived values must be plausible, never fabricated sentinels.
    for product in products:
        if product["sentiment"] is not None:
            assert 0 <= product["sentiment"] <= 100
        if product["change"] is not None:
            assert -100 < product["change"] < 500
        assert product["color"].startswith("#")
        assert isinstance(product["specs"], dict)


def test_products_search_and_filter(client):
    by_search = client.get("/api/products", params={"search": "Apple"}).json()
    assert by_search, "search for Apple returned nothing"
    assert all("apple" in (p["brand"] + p["name"]).lower() for p in by_search)

    by_brand = client.get("/api/products", params={"brand": "Sony"}).json()
    assert by_brand
    assert all(p["brand"] == "Sony" for p in by_brand)

    by_price = client.get("/api/products", params={"min_price": 5000}).json()
    assert all(p["price"] >= 5000 for p in by_price)


def test_product_detail_has_history_and_reviews(client):
    products = client.get("/api/products").json()
    product_id = products[0]["id"]

    response = client.get(f"/api/products/{product_id}")
    assert response.status_code == 200
    detail = response.json()

    assert detail["product"]["id"] == product_id
    assert isinstance(detail["price_history"], list)
    assert isinstance(detail["reviews"], list)
    assert detail["review_summary_source"] in ("llm", "unavailable")
    for point in detail["price_history"]:
        assert point["price"] > 0


def test_product_404(client):
    assert client.get("/api/products/999999").status_code == 404


def test_compare_requires_two_ids(client):
    ids = [p["id"] for p in client.get("/api/products").json()[:2]]
    response = client.get("/api/products/compare", params={"ids": f"{ids[0]},{ids[1]}"})
    assert response.status_code == 200
    compared = response.json()
    assert [item["id"] for item in compared] == ids

    assert client.get("/api/products/compare", params={"ids": str(ids[0])}).status_code == 422
    assert client.get("/api/products/compare", params={"ids": "a,b"}).status_code == 422


def test_overview_shape(client):
    response = client.get("/api/analytics/overview")
    assert response.status_code == 200
    body = response.json()

    assert len(body["kpis"]) == 4
    for kpi in body["kpis"]:
        assert {"label", "value", "tone", "icon"} <= set(kpi)

    assert body["evolution"], "evolution series is empty"
    for point in body["evolution"]:
        assert "month" in point

    assert body["mentions"], "no mentions returned"
    for mention in body["mentions"]:
        assert {"id", "brand", "text", "source", "sentiment"} <= set(mention)

    assert body["product_count"] >= 5
    assert body["brand_count"] >= 3


def test_sentiment_dashboard_shape(client):
    response = client.get("/api/analytics/sentiment")
    assert response.status_code == 200
    body = response.json()

    assert len(body["distribution"]) == 3
    total = sum(item["value"] for item in body["distribution"])
    assert 99.0 <= total <= 101.0, f"distribution does not sum to 100: {total}"

    assert body["total_reviews"] > 0
    assert body["aspects"], "no aspect scores"
    for aspect in body["aspects"]:
        assert 0 <= aspect["score"] <= 100

    assert body["keywords"], "no keywords"
    for keyword in body["keywords"]:
        assert keyword["tone"] in ("positive", "neutral", "negative")

    assert body["reviews"]
    for review in body["reviews"]:
        assert review["sentiment"] in ("positive", "neutral", "negative")


def test_sentiment_filters(client):
    all_reviews = client.get("/api/analytics/sentiment").json()["total_reviews"]
    sony = client.get("/api/analytics/sentiment", params={"brand": "Sony"}).json()
    assert 0 < sony["total_reviews"] < all_reviews

    emag = client.get("/api/analytics/sentiment", params={"source": "eMAG"}).json()
    assert 0 < emag["total_reviews"] <= all_reviews


def test_brand_stats_shape(client):
    response = client.get("/api/analytics/brands")
    assert response.status_code == 200
    brands = response.json()
    assert len(brands) >= 3

    total_share = sum(item["shareOfVoice"] for item in brands)
    assert 99.0 <= total_share <= 101.0

    for brand in brands:
        assert brand["color"].startswith("#")
        assert brand["mentions"] > 0
        assert isinstance(brand["topics"], list)
        assert isinstance(brand["concerns"], list)


def test_consumer_segments_shape(client):
    response = client.get("/api/analytics/consumer-segments")
    assert response.status_code == 200
    segments = response.json()
    assert segments

    total = sum(segment["sizeValue"] for segment in segments)
    assert 99.0 <= total <= 101.0

    for segment in segments:
        assert 0 <= segment["loyalty"] <= 100
        assert 0 <= segment["sensitivity"] <= 100
        assert segment["preferences"]


def test_competitors_shape(client):
    response = client.get("/api/analytics/competitors")
    assert response.status_code == 200
    body = response.json()

    assert body["brands"]
    assert body["priceDifferences"]
    assert len(body["features"]) == 6

    for row in body["matrix"]:
        assert len(row["values"]) == len(body["features"])
        for value in row["values"]:
            assert value is None or 0 <= value <= 100

    for row in body["priceDifferences"]:
        assert abs((row["price"] - row["baseline"]) - row["difference"]) < 0.02


def test_marketing_dashboard_shape(client):
    response = client.get("/api/marketing/trends")
    assert response.status_code == 200
    body = response.json()

    assert body["trends"]
    assert len(body["kpis"]) == 4
    assert body["opportunities"]
    assert body["opportunities_source"] in ("llm", "derived")
    assert body["source_volume"]

    for opportunity in body["opportunities"]:
        assert {"title", "type", "detail", "impact", "color"} <= set(opportunity)


def test_recommendations_shape(client):
    response = client.get("/api/analytics/recommendations")
    assert response.status_code == 200
    body = response.json()

    assert body["items"]
    assert body["summary"]["source"] in ("llm", "derived")
    assert body["summary"]["headline"]

    for item in body["items"]:
        assert item["category"] in ("Product", "Consumer", "Marketing", "Competitive")
        assert item["priority"] in ("High", "Medium", "Low")
        assert 0 <= item["confidence"] <= 100
        assert item["route"].startswith("/")


def test_recommendations_category_filter(client):
    all_items = client.get("/api/analytics/recommendations").json()["items"]
    product_items = client.get("/api/analytics/recommendations", params={"category": "Product"}).json()["items"]
    assert product_items
    assert all(item["category"] == "Product" for item in product_items)
    assert len(product_items) <= len(all_items)


def test_legacy_endpoints_still_work(client):
    """The original backend contract is kept for backwards compatibility."""
    assert client.get("/api/analytics/summary").status_code == 200
    assert client.get("/api/analytics/product-sentiment", params={"product_id": 1}).status_code == 200
    assert client.get("/api/analytics/prices", params={"product_id": 1}).status_code == 200
    assert client.get("/api/analytics/trends").status_code == 200
    assert client.get("/api/analytics/product-recommendations").status_code == 200
    assert client.get("/api/products/1/detail").status_code == 200
    assert client.get("/api/products/1/prices").status_code == 200
    assert client.get("/api/products/1/reviews").status_code == 200


def test_price_change_uses_oldest_point(client):
    """
    Regression: forecasting used prices[-1] as "oldest", so the change was always
    ~0. The seeded history starts above the current price, so the change must be
    non-zero for at least one product.
    """
    products = client.get("/api/products").json()
    changes = [p["change"] for p in products if p["change"] is not None]
    assert changes, "no product reported a price change"
    assert any(abs(change) > 0.5 for change in changes), (
        f"every price change is ~0, the oldest/newest inversion is back: {changes}"
    )
