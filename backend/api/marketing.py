import json
import logging
from typing import List, Dict, Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from database.connection import get_db
from database.models import Review as ReviewModel, Product as ProductModel
from schemas.dto import MarketingDashboard, MarketingTrendPoint, MarketingOpportunity, Kpi
from services.analytics_service import analytics_service, ASPECT_LABELS
from services.llm_service import llm_service

logger = logging.getLogger("marketpulse.api.marketing")

router = APIRouter(
    prefix="/api/marketing",
    tags=["Marketing"]
)


def _derived_opportunities(db: Session) -> List[Dict[str, Any]]:
    """
    Opportunities built from the same stored signals as the recommendations,
    phrased for a marketing audience. Used when no LLM is configured.
    """
    brand_stats = analytics_service.brand_stats(db)
    segments = analytics_service.consumer_segments(db)
    reviews = db.query(ReviewModel).all()
    aspects = analytics_service.aspect_breakdown(reviews)

    opportunities: List[Dict[str, Any]] = []

    if brand_stats:
        strongest = max(
            [b for b in brand_stats if b["sentiment"] is not None],
            key=lambda b: b["sentiment"],
            default=None,
        )
        if strongest and strongest["topics"]:
            opportunities.append({
                "title": f"Turn {strongest['brand']} praise into proof",
                "type": "CONTENT OPPORTUNITY",
                "detail": (
                    f"{strongest['brand']} scores {strongest['sentiment']:.0f}/100 across "
                    f"{strongest['mentions']} mentions. {strongest['topics'][0]} is the "
                    f"theme reviewers return to most."
                ),
                "impact": "High potential",
                "color": "var(--positive)",
            })

    if segments:
        largest = max(segments, key=lambda s: s["sizeValue"])
        opportunities.append({
            "title": f"Meet {largest['name'].lower()} where they are",
            "type": "AUDIENCE OPPORTUNITY",
            "detail": (
                f"{largest['name']} represent {largest['size']} of analysed reviews with an "
                f"average product price of {largest['spend']} and a loyalty score of "
                f"{largest['loyalty']:.0f}/100."
            ),
            "impact": "Growing demand",
            "color": "var(--accent)",
        })

    if aspects:
        weakest = min(aspects.items(), key=lambda kv: kv[1]["score"])
        label = ASPECT_LABELS.get(weakest[0], weakest[0].title())
        opportunities.append({
            "title": f"Address the {label.lower()} narrative",
            "type": "NARRATIVE OPPORTUNITY",
            "detail": (
                f"{label} is the lowest-scoring aspect at {weakest[1]['score']:.0f}/100, "
                f"with {weakest[1]['negative']} negative mentions across the stored reviews."
            ),
            "impact": "Emerging signal",
            "color": "var(--neutral)",
        })

    return opportunities[:3]


@router.get("/trends", response_model=MarketingDashboard)
def get_marketing_dashboard(db: Session = Depends(get_db)):
    """
    Marketing analytics: weekly mention volume per brand and source, opportunity
    cards, KPI row and source distribution. The narrative is rewritten by the LLM
    when one is configured; the numbers never are.
    """
    trends = analytics_service.marketing_trends(db)
    source_volume = analytics_service.source_volume(db)
    reviews = db.query(ReviewModel).all()
    sentiment = analytics_service.product_sentiment(reviews)

    total_mentions = len(reviews)
    # Peak across every brand series, not just Apple's: the previous version
    # reported Apple's maximum as if it were the market-wide peak.
    brand_keys = ["Apple", "NVIDIA", "Microsoft", "Samsung", "Sony"]
    peak_interest = (
        max(
            (point.get(brand) or 0.0 for point in trends for brand in brand_keys),
            default=0.0,
        )
        if trends else None
    )

    kpis = [
        Kpi(
            # The series is indexed against the busiest week's TOTAL mentions, so
            # a single brand peaks well below 100. Labelling this "search
            # interest /100" would read as a market-wide score; it is not.
            label="Peak brand index",
            value=f"{peak_interest:.1f}" if peak_interest is not None else "—",
            suffix="/ 100" if peak_interest is not None else None,
            change=None,
            note="highest single-brand week" if peak_interest is not None else "not enough data",
            tone="neutral",
            icon="trend",
            spark=[],
        ),
        Kpi(
            label="Social mentions",
            value=f"{total_mentions}",
            change=None,
            note=f"across {len(source_volume)} sources",
            tone="neutral",
            icon="message",
            spark=[],
        ),
        Kpi(
            label="Campaign sentiment",
            value=f"{sentiment:.0f}" if sentiment is not None else "—",
            suffix="/ 100" if sentiment is not None else None,
            change=None,
            note="not enough data" if sentiment is None else "all stored reviews",
            tone="positive" if sentiment and sentiment >= 60 else "neutral",
            icon="heart",
            spark=[],
        ),
        Kpi(
            label="Share of voice",
            value=(
                f"{max((b['shareOfVoice'] for b in analytics_service.brand_stats(db)), default=0):.1f}"
                if analytics_service.brand_stats(db) else "—"
            ),
            suffix="%" if analytics_service.brand_stats(db) else None,
            change=None,
            note="leading brand",
            tone="neutral",
            icon="layers",
            spark=[],
        ),
    ]

    # Opportunities: LLM when configured, derived otherwise.
    opportunities: List[Dict[str, Any]] = []
    source = "derived"
    if llm_service.enabled and reviews:
        payload = {
            "total_mentions": total_mentions,
            "average_sentiment": sentiment,
            "source_volume": source_volume,
            "brand_stats": [
                {"brand": b["brand"], "mentions": b["mentions"], "sentiment": b["sentiment"]}
                for b in analytics_service.brand_stats(db)
            ],
            "weakest_aspects": [
                {"aspect": ASPECT_LABELS.get(name, name), "score": data["score"]}
                for name, data in sorted(
                    analytics_service.aspect_breakdown(reviews).items(),
                    key=lambda kv: kv[1]["score"],
                )[:3]
            ],
        }
        raw = llm_service.marketing_opportunities(payload, db)
        if raw:
            try:
                parsed = json.loads(raw.strip().removeprefix("```json").removesuffix("```").strip())
                if isinstance(parsed, list) and parsed:
                    colors = ["var(--positive)", "var(--accent)", "var(--neutral)"]
                    opportunities = [
                        {
                            "title": str(item.get("title", ""))[:80],
                            "type": str(item.get("type", "CONTENT OPPORTUNITY"))[:40],
                            "detail": str(item.get("detail", ""))[:220],
                            "impact": str(item.get("impact", ""))[:24],
                            "color": colors[index % len(colors)],
                        }
                        for index, item in enumerate(parsed[:3])
                    ]
                    source = "llm"
            except Exception:
                logger.warning("LLM opportunities were not valid JSON; using the derived set")

    if not opportunities:
        opportunities = _derived_opportunities(db)

    return MarketingDashboard(
        trends=[MarketingTrendPoint(**point) for point in trends],
        opportunities=[MarketingOpportunity(**item) for item in opportunities],
        opportunities_source=source,
        kpis=kpis,
        source_volume=source_volume,
    )
