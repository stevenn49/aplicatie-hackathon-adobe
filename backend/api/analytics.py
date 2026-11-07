import json
import logging
from typing import Optional, List
from fastapi import APIRouter, Query, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from database.connection import get_db
from database.models import Product as ProductModel, Review as ReviewModel, PriceHistory as PriceHistoryModel, TrendMetric as TrendMetricModel
from schemas.analytics import (
    AnalyticsOverview,
    SentimentAnalysis,
    PriceAnalysis,
    TrendAnalysis,
    Recommendation
)
from schemas.dto import (
    MarketOverview,
    SentimentDashboard,
    BrandStat,
    ConsumerSegment,
    CompetitorDashboard,
    RecommendationsDashboard,
    ExecutiveSummary,
    InsightCard,
)
from services.sentiment_analysis import sentiment_service
from services.forecasting import forecasting_service
from services.recommendations import recommendation_service
from services.analytics_service import analytics_service, ASPECT_LABELS
from services.llm_service import llm_service
from data_collection.trends import trend_collector

logger = logging.getLogger("marketpulse.api.analytics")

router = APIRouter(
    prefix="/api/analytics",
    tags=["Analytics"]
)


# --------------------------------------------------------------------------- #
# Dashboard endpoints (the shapes the React app consumes)
# --------------------------------------------------------------------------- #

@router.get("/overview", response_model=MarketOverview)
def get_overview(db: Session = Depends(get_db)):
    """
    Market overview: KPIs, weekly conversation volume per brand, recent mentions
    and the biggest price movers. Every value is computed from stored rows.
    """
    return MarketOverview(**analytics_service.overview(db))


@router.get("/sentiment", response_model=SentimentDashboard)
def get_sentiment_dashboard(
    product_id: Optional[int] = Query(None, gt=0, description="Restrict to one product"),
    brand: Optional[str] = Query(None, description="Restrict to one brand"),
    source: Optional[str] = Query(None, description="Restrict to one source"),
    db: Session = Depends(get_db)
):
    """
    Sentiment dashboard across all reviews (or a filtered subset):
    distribution, weekly trend, aspect scores, keyword cloud and the review list.
    """
    query = db.query(ReviewModel).join(ProductModel, ReviewModel.product_id == ProductModel.id)

    if product_id:
        product = db.query(ProductModel).filter(ProductModel.id == product_id).first()
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with ID {product_id} not found"
            )
        query = query.filter(ReviewModel.product_id == product_id)
    if brand:
        query = query.filter(ProductModel.brand.ilike(brand.strip()))
    if source:
        query = query.filter(ReviewModel.source.ilike(source.strip()))

    reviews = query.all()

    aspects = analytics_service.aspect_breakdown(reviews)
    aspect_rows = [
        {
            "aspect": ASPECT_LABELS.get(name, name.title()),
            "score": data["score"],
            "mentions": data["total"],
        }
        for name, data in sorted(aspects.items(), key=lambda kv: kv[1]["score"], reverse=True)
    ]

    review_rows = []
    for review in sorted(
        reviews,
        key=lambda r: r.published_at or r.created_at or 0,
        reverse=True,
    )[:50]:
        product = review.product
        when = review.published_at or review.created_at
        review_rows.append({
            "id": review.id,
            "author": review.author or "Anonymous",
            "brand": product.brand if product else "Unknown",
            "product": product.name if product else "Unknown",
            "text": review.content,
            "rating": review.rating,
            "sentiment": review.sentiment_label or "neutral",
            "source": review.source,
            "date": when.strftime("%b %d, %Y") if when else "",
            "helpful": review.helpful,
        })

    return SentimentDashboard(
        distribution=analytics_service.distribution(reviews),
        trend=analytics_service.sentiment_trend(db),
        aspects=aspect_rows,
        keywords=analytics_service.keyword_cloud(reviews),
        reviews=review_rows,
        total_reviews=len(reviews),
    )


@router.get("/brands", response_model=List[BrandStat])
def get_brand_stats(
    brand: Optional[str] = Query(None, description="Restrict to one brand"),
    db: Session = Depends(get_db)
):
    """
    Brand intelligence: share of voice, mention volume, sentiment, health score,
    and the themes that drive praise or criticism.
    """
    stats = analytics_service.brand_stats(db)
    if brand:
        stats = [item for item in stats if item["brand"].lower() == brand.strip().lower()]
    return stats


@router.get("/consumer-segments", response_model=List[ConsumerSegment])
def get_consumer_segments(db: Session = Depends(get_db)):
    """
    Consumer segments derived from what reviewers actually discuss.
    """
    return analytics_service.consumer_segments(db)


@router.get("/competitors", response_model=CompetitorDashboard)
def get_competitors(db: Session = Depends(get_db)):
    """
    Competitive positioning: brand shares, price differences against the category
    median, and a feature matrix built from aspect sentiment.
    """
    return CompetitorDashboard(**analytics_service.competitor_dashboard(db))


@router.get("/recommendations", response_model=RecommendationsDashboard)
def get_recommendations(
    category: Optional[str] = Query(None, description="Product | Consumer | Marketing | Competitive"),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """
    Recommendations with an executive summary. The numbers always come from the
    derived engine; the wording is rewritten by the LLM when one is configured,
    and the response says which source produced the text.
    """
    items = analytics_service.recommendations(db)
    if category and category.lower() != "all":
        items = [item for item in items if item["category"].lower() == category.lower()]
    items = items[:limit]

    high_priority = sum(1 for item in items if item["priority"] == "High")
    avg_confidence = (
        round(sum(item["confidence"] for item in items) / len(items), 1) if items else None
    )

    # Readiness: 70 % average sentiment, 30 % inverse high-priority share.
    reviews = db.query(ReviewModel).all()
    sentiment = analytics_service.product_sentiment(reviews)
    readiness = None
    if sentiment is not None:
        pressure = min(100.0, high_priority * 12.0)
        readiness = round(0.7 * sentiment + 0.3 * (100.0 - pressure), 1)

    summary_text = None
    if items:
        payload = {
            "average_sentiment": sentiment,
            "readiness": readiness,
            "high_priority": high_priority,
            "recommendations": [
                {
                    "category": item["category"],
                    "priority": item["priority"],
                    "title": item["title"],
                    "metric": item["metric"],
                }
                for item in items[:8]
            ],
        }
        raw = llm_service.executive_summary(payload, db)
        if raw:
            try:
                parsed = json.loads(raw.strip().removeprefix("```json").removesuffix("```").strip())
                summary_text = (
                    str(parsed.get("headline", "")).strip(),
                    str(parsed.get("body", "")).strip(),
                )
            except Exception:
                logger.warning("LLM executive summary was not valid JSON; using the derived text")

    if summary_text:
        headline, body = summary_text
        source = "llm"
    else:
        top = items[0] if items else None
        headline = (
            f"Highest-impact move: {top['title'][0].lower()}{top['title'][1:]}."
            if top else "Not enough data for a recommendation yet."
        )
        body = (
            f"{len(items)} signals were derived from {len(reviews)} stored reviews"
            + (f" at an average sentiment of {sentiment:.0f}/100" if sentiment is not None else "")
            + (f", with {high_priority} high-priority action{'s' if high_priority != 1 else ''}" if high_priority else "")
            + ". Open any item to see the evidence behind it."
            if items else
            "Collect reviews for at least one product and the engine will produce recommendations."
        )
        source = "derived"

    return RecommendationsDashboard(
        summary=ExecutiveSummary(
            headline=headline,
            body=body,
            source=source,
            readiness=readiness,
            avg_confidence=avg_confidence,
        ),
        items=[InsightCard(**item) for item in items],
        high_priority=high_priority,
    )


# --------------------------------------------------------------------------- #
# Legacy endpoints kept for backwards compatibility
# --------------------------------------------------------------------------- #

@router.get("/summary", response_model=AnalyticsOverview)
def get_summary(db: Session = Depends(get_db)):
    """
    Aggregate counters (the original /overview contract).
    """
    total_products = db.query(func.count(ProductModel.id)).scalar() or 0
    avg_price = db.query(func.avg(ProductModel.price)).scalar() or 0.0
    total_reviews = db.query(func.count(ReviewModel.id)).scalar() or 0
    avg_rating = db.query(func.avg(ProductModel.rating)).filter(ProductModel.rating > 0).scalar()

    distinct_brands = db.query(func.count(func.distinct(ProductModel.brand))).scalar() or 0
    distinct_categories = db.query(func.count(func.distinct(ProductModel.category))).scalar() or 0

    return AnalyticsOverview(
        total_products=total_products,
        average_price=round(float(avg_price), 2),
        total_reviews=total_reviews,
        average_rating=round(float(avg_rating), 2) if avg_rating else 0.0,
        brands_tracked=distinct_brands,
        categories_tracked=distinct_categories
    )


@router.get("/product-sentiment", response_model=SentimentAnalysis)
def get_product_sentiment(product_id: int = Query(..., gt=0), db: Session = Depends(get_db)):
    """
    Sentiment breakdown for a single product (the original contract).
    """
    product = db.query(ProductModel).filter(ProductModel.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found"
        )

    reviews = db.query(ReviewModel).filter(ReviewModel.product_id == product_id).all()
    aggregated = sentiment_service.aggregate_reviews(
        product_id=product.id,
        product_name=product.name,
        reviews=reviews
    )

    return SentimentAnalysis(**aggregated)


@router.get("/prices", response_model=PriceAnalysis)
def get_price_analysis(product_id: int = Query(..., gt=0), db: Session = Depends(get_db)):
    """
    Price dynamics for a single product: current, min, max, average and change.
    """
    product = db.query(ProductModel).filter(ProductModel.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found"
        )

    price_history = (
        db.query(PriceHistoryModel)
        .filter(PriceHistoryModel.product_id == product_id)
        .order_by(PriceHistoryModel.recorded_at.asc())
        .all()
    )

    analysis = forecasting_service.analyze_price_history(
        product_id=product.id,
        product_name=product.name,
        current_price=product.price,
        price_history=price_history,
        currency=product.currency
    )

    return PriceAnalysis(**analysis)


@router.get("/trends", response_model=List[TrendAnalysis])
def get_trends(category: Optional[str] = Query(None), db: Session = Depends(get_db)):
    """
    Market trend indicators by category.
    """
    query = db.query(TrendMetricModel)
    if category:
        query = query.filter(TrendMetricModel.category.ilike(category.strip()))

    recorded_trends = query.order_by(TrendMetricModel.trend_score.desc()).all()

    if recorded_trends:
        results = []
        for t in recorded_trends:
            brands = [
                b[0] for b in db.query(ProductModel.brand)
                .filter(ProductModel.category.ilike(t.category))
                .distinct()
                .limit(5)
                .all()
            ]
            results.append(
                TrendAnalysis(
                    category=t.category,
                    trend_score=round(t.trend_score, 1),
                    trend_direction=t.trend_direction,
                    search_interest=round(t.search_interest, 1),
                    top_brands=brands
                )
            )
        return results

    distinct_categories = [
        c[0] for c in db.query(ProductModel.category).distinct().all()
    ]

    results = []
    for cat in distinct_categories:
        if category and category.lower() != cat.lower():
            continue

        prod_count = db.query(func.count(ProductModel.id)).filter(ProductModel.category == cat).scalar() or 0
        review_count = (
            db.query(func.count(ReviewModel.id))
            .join(ProductModel, ReviewModel.product_id == ProductModel.id)
            .filter(ProductModel.category == cat)
            .scalar() or 0
        )
        brands = [
            b[0] for b in db.query(ProductModel.brand)
            .filter(ProductModel.category == cat)
            .distinct()
            .limit(5)
            .all()
        ]

        trend_score = min(100.0, max(20.0, (prod_count * 15.0) + (review_count * 2.5)))
        results.append(
            TrendAnalysis(
                category=cat,
                trend_score=round(trend_score, 1),
                trend_direction="increasing" if trend_score > 60 else "stable",
                search_interest=round(trend_score * 0.9, 1),
                top_brands=brands
            )
        )

    return results


@router.get("/product-recommendations", response_model=List[Recommendation])
def get_product_recommendations(
    category: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """
    Per-product buy/wait advice (the original contract).
    """
    query = db.query(ProductModel)
    if category:
        query = query.filter(ProductModel.category.ilike(category.strip()))

    products = query.limit(limit).all()
    if not products:
        return []

    sentiment_map = {}
    for p in products:
        revs = db.query(ReviewModel).filter(ReviewModel.product_id == p.id).all()
        sentiment_map[p.id] = sentiment_service.aggregate_reviews(p.id, p.name, revs)

    return recommendation_service.generate_recommendations(
        products=products,
        sentiment_data=sentiment_map
    )


@router.post("/refresh-trends", response_model=List[TrendAnalysis])
def refresh_market_trends(db: Session = Depends(get_db)):
    """
    Refresh Google Trends metrics for the tracked categories.
    """
    trend_collector.refresh_trends(db)
    return get_trends(db=db)
