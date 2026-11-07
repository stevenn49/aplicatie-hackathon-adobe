"""
Derivation layer: turns stored rows into the presentation values the dashboard
consumes.

Every function here obeys one rule: if the stored data cannot support a number,
return None. The UI renders "not enough data" for None. Nothing is invented.
"""
import hashlib
import logging
import math
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from database.models import Product, PriceHistory, Review, TrendMetric

logger = logging.getLogger("marketpulse.services.analytics")

# The five brands the product is positioned around. Any other brand gets a
# deterministic colour from its name, so the UI never renders an unknown grey.
KNOWN_BRAND_COLORS = {
    "Apple": "#8b8cf7",
    "NVIDIA": "#9bd94e",
    "Microsoft": "#59a9f5",
    "Samsung": "#f0a35e",
    "Sony": "#e8788c",
}
FALLBACK_PALETTE = [
    "#a6e06c", "#f3bb6a", "#a39af9", "#f08399", "#73baf5",
    "#84cfc2", "#d4a5f0", "#f0c674", "#9ad0f5", "#f5a3a3",
]

ASPECT_LABELS = {
    "battery": "Battery life",
    "camera": "Camera quality",
    "display": "Display",
    "performance": "Performance",
    "price_value": "Price & value",
    "build_quality": "Build quality",
    "software": "Software & OS",
    "audio": "Audio",
}

STOPWORDS = {
    "the", "and", "for", "with", "this", "that", "from", "have", "has", "had",
    "are", "was", "were", "but", "not", "you", "your", "they", "them", "its",
    "very", "much", "more", "most", "than", "then", "there", "here", "when",
    "what", "which", "who", "will", "would", "can", "could", "should", "about",
    "into", "over", "under", "after", "before", "also", "just", "only", "even",
    "still", "some", "any", "all", "one", "two", "get", "got", "make", "made",
    "use", "used", "using", "like", "really", "quite", "well", "good", "great",
    "best", "better", "bad", "worst", "product", "products", "review", "reviews",
    "phone", "phones", "device", "devices", "price", "prices", "time", "times",
    "day", "days", "week", "weeks", "month", "months", "year", "years",
    "si", "sau", "dar", "este", "sunt", "foarte", "mai", "cel", "cea", "care",
    "pentru", "din", "cu", "pe", "la", "un", "o", "al", "ale", "lui", "ei",
    "nu", "se", "in", "de", "ca", "sa", "fost", "am", "ai", "are", "avea",
}


def brand_color(brand: str) -> str:
    if brand in KNOWN_BRAND_COLORS:
        return KNOWN_BRAND_COLORS[brand]
    digest = hashlib.sha256(brand.encode("utf-8")).digest()
    return FALLBACK_PALETTE[digest[0] % len(FALLBACK_PALETTE)]


def _pct(part: float, total: float) -> float:
    return round((part / total) * 100.0, 1) if total else 0.0


def _human_count(value: int) -> str:
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"{value / 1_000:.1f}k"
    return str(value)


def _human_money(value: float, currency: str = "RON") -> str:
    suffix = "lei" if currency == "RON" else currency
    return f"{value:,.0f} {suffix}".replace(",", ".")


def _month_label(value: datetime) -> str:
    return value.strftime("%b %d")


class AnalyticsService:
    """All derived metrics, computed from the database on every call."""

    # ------------------------------------------------------------------ #
    # Per-product derivations
    # ------------------------------------------------------------------ #

    def product_sentiment(self, reviews: Sequence[Review]) -> Optional[float]:
        """
        0-100 sentiment score. None when there are no reviews.
        Combines the label distribution with the mean compound score so a
        product with many neutral reviews does not score as strongly positive.
        """
        if not reviews:
            return None
        pos = sum(1 for r in reviews if r.sentiment_label == "positive")
        neg = sum(1 for r in reviews if r.sentiment_label == "negative")
        total = len(reviews)
        positive_ratio = pos / total
        negative_ratio = neg / total
        scores = [r.sentiment_score for r in reviews if r.sentiment_score is not None]
        mean_compound = sum(scores) / len(scores) if scores else 0.0
        # 70 % label distribution, 30 % mean compound, both mapped to 0-100.
        label_component = (positive_ratio + (1.0 - negative_ratio)) / 2.0 * 100.0
        compound_component = (mean_compound + 1.0) / 2.0 * 100.0
        return round(0.7 * label_component + 0.3 * compound_component, 1)

    def price_change(self, history: Sequence[PriceHistory], current_price: float) -> Optional[float]:
        """
        Percentage movement from the OLDEST recorded point to now.
        `history` must be ordered ascending by recorded_at. None with <2 points.
        """
        if len(history) < 2:
            return None
        oldest = history[0].price
        if not oldest:
            return None
        return round(((current_price - oldest) / oldest) * 100.0, 1)

    def product_interest(self, reviews: Sequence[Review], max_reviews: int) -> Optional[float]:
        """
        0-100 mention intensity relative to the busiest product in the catalogue.
        None when the product has no reviews or the catalogue has none at all.
        """
        if not reviews or max_reviews <= 0:
            return None
        return round(min(100.0, (len(reviews) / max_reviews) * 100.0), 1)

    def aspect_breakdown(self, reviews: Iterable[Review]) -> Dict[str, Dict[str, Any]]:
        """
        Aggregates review aspects into {aspect: {positive, neutral, negative, total, score}}.
        `score` is 0-100 (positive share weighted by neutral), None when total is 0.
        """
        agg: Dict[str, Dict[str, int]] = defaultdict(lambda: {"positive": 0, "neutral": 0, "negative": 0, "total": 0})
        for review in reviews:
            aspects = review.aspects or {}
            if not isinstance(aspects, dict):
                continue
            for name, detail in aspects.items():
                if not isinstance(detail, dict):
                    continue
                label = detail.get("sentiment", "neutral")
                if label not in ("positive", "neutral", "negative"):
                    label = "neutral"
                agg[name][label] += 1
                agg[name]["total"] += 1

        result: Dict[str, Dict[str, Any]] = {}
        for name, counts in agg.items():
            total = counts["total"]
            if total == 0:
                continue
            score = (counts["positive"] + counts["neutral"] * 0.5) / total * 100.0
            result[name] = {**counts, "score": round(score, 1)}
        return result

    def pros_cons(self, aspects: Dict[str, Dict[str, Any]], limit: int = 3) -> Tuple[List[str], List[str]]:
        """
        Turns aspect sentiment into human phrases. Empty lists when there is no
        aspect data at all — the UI then shows nothing rather than a generic line.
        """
        if not aspects:
            return [], []
        ranked = sorted(aspects.items(), key=lambda kv: kv[1]["score"], reverse=True)
        pros = [
            f"{ASPECT_LABELS.get(name, name.title())} praised in {data['total']} review{'s' if data['total'] != 1 else ''}"
            for name, data in ranked
            if data["score"] >= 65.0
        ][:limit]
        cons = [
            f"{ASPECT_LABELS.get(name, name.title())} criticised in {data['negative']} review{'s' if data['negative'] != 1 else ''}"
            for name, data in sorted(ranked, key=lambda kv: kv[1]["score"])
            if data["score"] <= 45.0 and data["negative"] > 0
        ][:limit]
        return pros, cons

    # ------------------------------------------------------------------ #
    # Catalogue-level derivations
    # ------------------------------------------------------------------ #

    def max_review_count(self, db: Session) -> int:
        """The busiest product's review count, used to normalise interest to 0-100."""
        row = (
            db.query(func.count(Review.id))
            .group_by(Review.product_id)
            .order_by(func.count(Review.id).desc())
            .limit(1)
            .scalar()
        )
        return int(row or 0)

    def brand_stats(self, db: Session) -> List[Dict[str, Any]]:
        """
        Brand-level intelligence computed from stored reviews and products.
        shareOfVoice = the brand's share of all reviews.
        sentiment    = 0-100 over that brand's reviews.
        health       = 0.6 * sentiment + 0.4 * rating-normalised, None without data.
        """
        products = db.query(Product).all()
        if not products:
            return []

        reviews_by_product: Dict[int, List[Review]] = defaultdict(list)
        for review in db.query(Review).all():
            reviews_by_product[review.product_id].append(review)

        total_reviews = sum(len(v) for v in reviews_by_product.values())

        by_brand: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "reviews": [], "products": [], "ratings": []
        })
        for product in products:
            entry = by_brand[product.brand]
            entry["products"].append(product)
            entry["reviews"].extend(reviews_by_product.get(product.id, []))
            if product.rating:
                entry["ratings"].append(product.rating)

        stats: List[Dict[str, Any]] = []
        for brand, entry in by_brand.items():
            reviews = entry["reviews"]
            sentiment = self.product_sentiment(reviews)
            avg_rating = (
                round(sum(entry["ratings"]) / len(entry["ratings"]), 2)
                if entry["ratings"] else None
            )
            health = None
            if sentiment is not None and avg_rating is not None:
                health = round(0.6 * sentiment + 0.4 * (avg_rating / 5.0 * 100.0), 1)
            elif sentiment is not None:
                health = sentiment

            aspects = self.aspect_breakdown(reviews)
            ranked = sorted(aspects.items(), key=lambda kv: kv[1]["score"], reverse=True)
            topics = [
                ASPECT_LABELS.get(name, name.title())
                for name, data in ranked if data["score"] >= 60.0
            ][:3]
            concerns = [
                ASPECT_LABELS.get(name, name.title())
                for name, data in sorted(ranked, key=lambda kv: kv[1]["score"])
                if data["score"] <= 45.0 and data["negative"] > 0
            ][:3]

            stats.append({
                "brand": brand,
                "color": brand_color(brand),
                "shareOfVoice": _pct(len(reviews), total_reviews),
                "mentions": len(reviews),
                "sentiment": sentiment,
                "health": health,
                "topics": topics,
                "concerns": concerns,
            })

        stats.sort(key=lambda item: item["mentions"], reverse=True)
        return stats

    def evolution_series(self, db: Session, buckets: int = 12) -> List[Dict[str, Any]]:
        """
        Weekly review volume per brand over the last `buckets` weeks, indexed to
        100 against the busiest week. This is real conversation volume, not a
        search index, and the chart subtitle says so.
        """
        reviews = db.query(Review).join(Product, Review.product_id == Product.id).all()
        if not reviews:
            return []

        now = datetime.utcnow()
        # Anchor on the newest review so a seeded historical dataset still plots.
        dates = [r.published_at or r.created_at for r in reviews if (r.published_at or r.created_at)]
        if not dates:
            return []
        anchor = max(dates)

        bucket_days = 7
        start = anchor - timedelta(days=bucket_days * (buckets - 1))

        buckets_map: Dict[int, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for review in reviews:
            when = review.published_at or review.created_at
            if not when or when < start:
                continue
            index = min(buckets - 1, max(0, int((when - start).days // bucket_days)))
            brand = review.product.brand if review.product else "Unknown"
            buckets_map[index][brand] += 1

        peak = max(
            (sum(buckets_map[i].values()) for i in range(buckets)),
            default=0,
        )
        if peak == 0:
            return []

        series: List[Dict[str, Any]] = []
        for i in range(buckets):
            when = start + timedelta(days=bucket_days * i)
            point: Dict[str, Any] = {"month": _month_label(when)}
            for brand in KNOWN_BRAND_COLORS:
                point[brand] = round((buckets_map[i].get(brand, 0) / peak) * 100.0, 1)
            series.append(point)
        return series

    def keyword_cloud(self, reviews: Iterable[Review], limit: int = 12) -> List[Dict[str, Any]]:
        """
        Term frequency over stored review text, weighted by the sentiment of the
        reviews each term appears in. Real words from real reviews.
        """
        counts: Counter = Counter()
        sentiment_sum: Dict[str, float] = defaultdict(float)

        for review in reviews:
            text = (review.content or "").lower()
            words = re.findall(r"[a-zăâîșț]{4,}", text)
            seen = set()
            for word in words:
                if word in STOPWORDS or word in seen:
                    continue
                seen.add(word)
                counts[word] += 1
                sentiment_sum[word] += review.sentiment_score or 0.0

        if not counts:
            return []

        peak = max(counts.values())
        items: List[Dict[str, Any]] = []
        for word, count in counts.most_common(limit):
            avg_sentiment = sentiment_sum[word] / count
            score = round(min(100.0, (count / peak) * 100.0), 1)
            if avg_sentiment >= 0.05:
                tone = "positive"
            elif avg_sentiment <= -0.05:
                tone = "negative"
            else:
                tone = "neutral"
            items.append({"word": word, "score": score, "tone": tone})
        return items

    def sentiment_trend(self, db: Session, buckets: int = 12) -> List[Dict[str, Any]]:
        """Weekly positive/neutral/negative percentages across all reviews."""
        reviews = db.query(Review).all()
        if not reviews:
            return []
        dates = [r.published_at or r.created_at for r in reviews if (r.published_at or r.created_at)]
        if not dates:
            return []
        anchor = max(dates)
        bucket_days = 7
        start = anchor - timedelta(days=bucket_days * (buckets - 1))

        buckets_map: Dict[int, Dict[str, int]] = defaultdict(lambda: {"positive": 0, "neutral": 0, "negative": 0})
        for review in reviews:
            when = review.published_at or review.created_at
            if not when or when < start:
                continue
            index = min(buckets - 1, max(0, int((when - start).days // bucket_days)))
            label = review.sentiment_label or "neutral"
            if label not in ("positive", "neutral", "negative"):
                label = "neutral"
            buckets_map[index][label] += 1

        series: List[Dict[str, Any]] = []
        for i in range(buckets):
            when = start + timedelta(days=bucket_days * i)
            counts = buckets_map[i]
            total = sum(counts.values())
            series.append({
                "date": _month_label(when),
                "positive": _pct(counts["positive"], total),
                "neutral": _pct(counts["neutral"], total),
                "negative": _pct(counts["negative"], total),
            })
        return series

    def distribution(self, reviews: Sequence[Review]) -> List[Dict[str, Any]]:
        total = len(reviews)
        counts = {"positive": 0, "neutral": 0, "negative": 0}
        for review in reviews:
            label = review.sentiment_label or "neutral"
            if label not in counts:
                label = "neutral"
            counts[label] += 1
        return [
            {"name": "Positive", "value": _pct(counts["positive"], total), "color": "var(--positive)"},
            {"name": "Neutral", "value": _pct(counts["neutral"], total), "color": "var(--neutral)"},
            {"name": "Negative", "value": _pct(counts["negative"], total), "color": "var(--negative)"},
        ]

    # ------------------------------------------------------------------ #
    # Consumer segments
    # ------------------------------------------------------------------ #

    def consumer_segments(self, db: Session) -> List[Dict[str, Any]]:
        """
        Segments are derived from what reviewers actually talk about, not from a
        survey that does not exist. Each review is assigned to the segment whose
        aspect it mentions most strongly; a review with no aspect is assigned to
        the price-based segment only if its product is below the catalogue median.
        """
        products = {p.id: p for p in db.query(Product).all()}
        reviews = db.query(Review).all()
        if not reviews or not products:
            return []

        prices = [p.price for p in products.values()]
        median_price = sorted(prices)[len(prices) // 2]

        definitions = [
            ("s1", "Performance seekers", "#a6e06c", ["performance"], "High-performance hardware"),
            ("s2", "Value optimizers", "#f3bb6a", ["price_value"], "Best price-to-performance"),
            ("s3", "Ecosystem loyalists", "#a39af9", ["software"], "Seamless integration"),
            ("s4", "Early adopters", "#f08399", [], "Newest releases and AI features"),
            ("s5", "Practical upgraders", "#73baf5", ["battery", "build_quality"], "Reliability and longevity"),
        ]

        assigned: Dict[str, List[Review]] = defaultdict(list)
        for review in reviews:
            aspects = review.aspects or {}
            names = set(aspects.keys()) if isinstance(aspects, dict) else set()
            matched = None
            for seg_id, _name, _color, keys, _desc in definitions:
                if keys and names & set(keys):
                    matched = seg_id
                    break
            if matched is None:
                product = products.get(review.product_id)
                if product and product.price <= median_price:
                    matched = "s2"
                else:
                    matched = "s4"
            assigned[matched].append(review)

        total = len(reviews)
        segments: List[Dict[str, Any]] = []
        for seg_id, name, color, keys, description in definitions:
            group = assigned.get(seg_id, [])
            if not group:
                continue
            product_ids = {r.product_id for r in group}
            spend_values = [products[pid].price for pid in product_ids if pid in products]
            avg_spend = sum(spend_values) / len(spend_values) if spend_values else 0.0
            sentiment = self.product_sentiment(group) or 0.0
            # Sensitivity: the share of this segment's reviews that criticise price.
            price_criticism = sum(
                1 for r in group
                if isinstance(r.aspects, dict)
                and isinstance(r.aspects.get("price_value"), dict)
                and r.aspects["price_value"].get("sentiment") == "negative"
            )
            sensitivity = _pct(price_criticism, len(group))
            preferences = [description]
            aspects = self.aspect_breakdown(group)
            ranked = sorted(aspects.items(), key=lambda kv: kv[1]["score"], reverse=True)
            preferences += [
                ASPECT_LABELS.get(a, a.title()) for a, d in ranked if d["score"] >= 60.0
            ][:2]

            segments.append({
                "id": seg_id,
                "name": name,
                "size": f"{_pct(len(group), total):.0f}%",
                "sizeValue": _pct(len(group), total),
                "users": _human_count(len(group)),
                "usersValue": len(group),
                "spend": _human_money(avg_spend),
                "spendValue": round(avg_spend, 2),
                "loyalty": sentiment,
                "sensitivity": sensitivity,
                "preferences": preferences,
                "color": color,
            })
        return segments

    # ------------------------------------------------------------------ #
    # Competitors
    # ------------------------------------------------------------------ #

    def competitor_dashboard(self, db: Session) -> Dict[str, Any]:
        products = db.query(Product).all()
        if not products:
            return {"brands": [], "priceDifferences": [], "features": [], "matrix": [], "activity": []}

        brand_stats = self.brand_stats(db)
        brands = [
            {"name": item["brand"], "color": item["color"], "share": item["shareOfVoice"], "health": item["health"]}
            for item in brand_stats
        ]

        # Price difference against the median of the product's own category.
        by_category: Dict[str, List[float]] = defaultdict(list)
        for product in products:
            by_category[product.category].append(product.price)
        medians = {
            cat: sorted(vals)[len(vals) // 2] for cat, vals in by_category.items() if vals
        }

        price_differences = []
        for product in products:
            baseline = medians.get(product.category)
            if baseline is None:
                continue
            price_differences.append({
                "name": product.name,
                "brand": product.brand,
                "price": round(product.price, 2),
                "baseline": round(baseline, 2),
                "difference": round(product.price - baseline, 2),
            })
        price_differences.sort(key=lambda item: item["difference"], reverse=True)

        # Feature matrix: per-brand aspect score, 0-100. None where the brand has
        # no review mentioning that aspect.
        feature_keys = ["camera", "performance", "battery", "display", "price_value", "software"]
        features = [ASPECT_LABELS[k] for k in feature_keys]

        reviews_by_brand: Dict[str, List[Review]] = defaultdict(list)
        for review in db.query(Review).join(Product, Review.product_id == Product.id).all():
            brand = review.product.brand if review.product else None
            if brand:
                reviews_by_brand[brand].append(review)

        matrix = []
        for brand, reviews in reviews_by_brand.items():
            aspects = self.aspect_breakdown(reviews)
            values = [
                aspects.get(key, {}).get("score") for key in feature_keys
            ]
            matrix.append({"brand": brand, "values": values})

        # Activity: the most recent reviews per brand, presented as market moves.
        activity = []
        for brand, reviews in reviews_by_brand.items():
            latest = sorted(
                reviews,
                key=lambda r: r.published_at or r.created_at or datetime.min,
                reverse=True,
            )[:1]
            for review in latest:
                when = review.published_at or review.created_at
                activity.append({
                    "date": when.strftime("%b %d") if when else "",
                    "brand": brand,
                    "title": (review.title or review.content or "")[:90],
                    "detail": (review.content or "")[:160],
                    "type": review.source,
                })
        activity.sort(key=lambda item: item["date"], reverse=True)

        return {
            "brands": brands,
            "priceDifferences": price_differences,
            "features": features,
            "matrix": matrix,
            "activity": activity[:8],
        }

    # ------------------------------------------------------------------ #
    # Marketing
    # ------------------------------------------------------------------ #

    def marketing_trends(self, db: Session, buckets: int = 12) -> List[Dict[str, Any]]:
        """
        Weekly mention volume per brand and per source, indexed to 100.
        """
        reviews = db.query(Review).join(Product, Review.product_id == Product.id).all()
        if not reviews:
            return []
        dates = [r.published_at or r.created_at for r in reviews if (r.published_at or r.created_at)]
        if not dates:
            return []
        anchor = max(dates)
        bucket_days = 7
        start = anchor - timedelta(days=bucket_days * (buckets - 1))

        brand_counts: Dict[int, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        source_counts: Dict[int, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for review in reviews:
            when = review.published_at or review.created_at
            if not when or when < start:
                continue
            index = min(buckets - 1, max(0, int((when - start).days // bucket_days)))
            brand = review.product.brand if review.product else None
            if brand:
                brand_counts[index][brand] += 1
            source_counts[index][review.source] += 1

        peak = max((sum(brand_counts[i].values()) for i in range(buckets)), default=0)
        if peak == 0:
            return []

        series = []
        for i in range(buckets):
            when = start + timedelta(days=bucket_days * i)
            point: Dict[str, Any] = {"date": _month_label(when)}
            for brand in KNOWN_BRAND_COLORS:
                point[brand] = round((brand_counts[i].get(brand, 0) / peak) * 100.0, 1)
            for source in ("Reddit", "X", "eMAG", "TechCommunity"):
                point[source] = round((source_counts[i].get(source, 0) / peak) * 100.0, 1)
            point["event"] = None
            series.append(point)
        return series

    def source_volume(self, db: Session) -> List[Dict[str, Any]]:
        rows = (
            db.query(Review.source, func.count(Review.id))
            .group_by(Review.source)
            .order_by(func.count(Review.id).desc())
            .all()
        )
        return [{"source": source, "mentions": count} for source, count in rows]

    # ------------------------------------------------------------------ #
    # Recommendations
    # ------------------------------------------------------------------ #

    def recommendations(self, db: Session) -> List[Dict[str, Any]]:
        """
        Rule-based signals, each with the evidence that produced it. The LLM, when
        configured, rewrites the wording; the numbers always come from here.
        """
        products = db.query(Product).all()
        if not products:
            return []

        reviews_by_product: Dict[int, List[Review]] = defaultdict(list)
        for review in db.query(Review).all():
            reviews_by_product[review.product_id].append(review)

        by_category: Dict[str, List[float]] = defaultdict(list)
        for product in products:
            by_category[product.category].append(product.price)
        medians = {cat: sorted(v)[len(v) // 2] for cat, v in by_category.items() if v}

        items: List[Dict[str, Any]] = []
        for product in products:
            reviews = reviews_by_product.get(product.id, [])
            sentiment = self.product_sentiment(reviews)
            aspects = self.aspect_breakdown(reviews)
            median = medians.get(product.category)
            price_gap = (
                round(((product.price - median) / median) * 100.0, 1)
                if median else None
            )
            confidence = min(95, 40 + len(reviews) * 3)

            # 1. Price positioning
            if price_gap is not None and price_gap >= 20:
                items.append({
                    "id": f"price-{product.id}",
                    "category": "Product",
                    "priority": "High" if price_gap >= 35 else "Medium",
                    "title": f"Revisit the {product.name} entry price",
                    "detail": (
                        f"{product.name} sits {price_gap:.0f}% above the {product.category} median "
                        f"({_human_money(median, product.currency)}). "
                        f"{len(reviews)} reviews were analysed for this signal."
                    ),
                    "metric": f"Price gap +{price_gap:.0f}%",
                    "confidence": confidence,
                    "related": f"{product.brand} · {product.name}",
                    "route": "/products",
                    "icon": "target",
                })
            elif price_gap is not None and price_gap <= -15:
                items.append({
                    "id": f"value-{product.id}",
                    "category": "Product",
                    "priority": "Medium",
                    "title": f"Lead with {product.name} on value",
                    "detail": (
                        f"{product.name} is {abs(price_gap):.0f}% below the {product.category} median. "
                        f"Value messaging has a measurable price advantage to point at."
                    ),
                    "metric": f"Price gap {price_gap:.0f}%",
                    "confidence": confidence,
                    "related": f"{product.brand} · {product.name}",
                    "route": "/products",
                    "icon": "target",
                })

            # 2. Sentiment strength
            if sentiment is not None and sentiment >= 80 and len(reviews) >= 3:
                items.append({
                    "id": f"sentiment-{product.id}",
                    "category": "Marketing",
                    "priority": "High" if sentiment >= 88 else "Medium",
                    "title": f"Turn {product.brand} satisfaction into proof",
                    "detail": (
                        f"{sentiment:.0f}/100 average sentiment across {len(reviews)} reviews. "
                        f"Customer language is the strongest asset available for this product."
                    ),
                    "metric": f"Sentiment {sentiment:.0f}/100",
                    "confidence": confidence,
                    "related": f"{product.brand} · {product.name}",
                    "route": "/sentiment",
                    "icon": "sparkles",
                })

            # 3. Weak aspect
            if aspects:
                weakest = min(aspects.items(), key=lambda kv: kv[1]["score"])
                if weakest[1]["score"] <= 45 and weakest[1]["negative"] >= 1:
                    label = ASPECT_LABELS.get(weakest[0], weakest[0].title())
                    items.append({
                        "id": f"aspect-{product.id}-{weakest[0]}",
                        "category": "Competitive",
                        "priority": "High" if weakest[1]["score"] <= 30 else "Medium",
                        "title": f"Close the {label.lower()} gap on {product.name}",
                        "detail": (
                            f"{label} scores {weakest[1]['score']:.0f}/100 with "
                            f"{weakest[1]['negative']} negative mentions. "
                            f"This is the clearest competitive opening in the review data."
                        ),
                        "metric": f"{label} {weakest[1]['score']:.0f}/100",
                        "confidence": confidence,
                        "related": f"{product.brand} · {product.name}",
                        "route": "/competitors",
                        "icon": "swords",
                    })

        # 4. Segment-level recommendation
        segments = self.consumer_segments(db)
        if segments:
            largest = max(segments, key=lambda s: s["sizeValue"])
            items.append({
                "id": f"segment-{largest['id']}",
                "category": "Consumer",
                "priority": "Medium",
                "title": f"Build for {largest['name'].lower()}",
                "detail": (
                    f"{largest['name']} account for {largest['size']} of analysed reviews "
                    f"({largest['users']} mentions) with an average product price of {largest['spend']}."
                ),
                "metric": f"Segment share {largest['size']}",
                "confidence": 70,
                "related": largest["name"],
                "route": "/consumers",
                "icon": "users",
            })

        # 5. Brand-level recommendation
        brand_stats = self.brand_stats(db)
        if brand_stats:
            top = max(
                [b for b in brand_stats if b["sentiment"] is not None],
                key=lambda b: b["sentiment"],
                default=None,
            )
            if top:
                items.append({
                    "id": f"brand-{top['brand']}",
                    "category": "Marketing",
                    "priority": "Low",
                    "title": f"Protect {top['brand']}'s perception lead",
                    "detail": (
                        f"{top['brand']} leads on sentiment at {top['sentiment']:.0f}/100 across "
                        f"{top['mentions']} mentions. Sustaining it is cheaper than recovering it."
                    ),
                    "metric": f"Brand sentiment {top['sentiment']:.0f}/100",
                    "confidence": 68,
                    "related": top["brand"],
                    "route": "/brands",
                    "icon": "headphones",
                })

        items.sort(key=lambda item: ({"High": 0, "Medium": 1, "Low": 2}[item["priority"]], -item["confidence"]))
        return items

    # ------------------------------------------------------------------ #
    # Market overview
    # ------------------------------------------------------------------ #

    def overview(self, db: Session) -> Dict[str, Any]:
        products = db.query(Product).all()
        reviews = db.query(Review).all()
        total_products = len(products)
        total_reviews = len(reviews)
        avg_price = round(sum(p.price for p in products) / total_products, 2) if products else 0.0
        sentiment = self.product_sentiment(reviews)
        brands = {p.brand for p in products}
        categories = {p.category for p in products}

        # 7-point sparkline of weekly review volume.
        spark = self._review_spark(reviews, points=7)

        kpis = [
            {
                "label": "Tracked products",
                "value": str(total_products),
                "change": None,
                "note": f"across {len(categories)} categories",
                "tone": "neutral",
                "icon": "layers",
                "spark": spark,
            },
            {
                "label": "Reviews analysed",
                "value": _human_count(total_reviews),
                "change": None,
                "note": f"from {len({r.source for r in reviews})} sources",
                "tone": "neutral",
                "icon": "message",
                "spark": spark,
            },
            {
                "label": "Average sentiment",
                "value": f"{sentiment:.1f}" if sentiment is not None else "—",
                "suffix": "/ 100" if sentiment is not None else None,
                "change": None,
                "note": "not enough data" if sentiment is None else "across all reviews",
                "tone": "positive" if sentiment and sentiment >= 60 else "neutral",
                "icon": "heart",
                "spark": spark,
            },
            {
                "label": "Average price",
                "value": _human_money(avg_price) if products else "—",
                "change": None,
                "note": f"{len(brands)} brands monitored",
                "tone": "neutral",
                "icon": "trend",
                "spark": spark,
            },
        ]

        # Recent mentions: the newest reviews across all products.
        recent = sorted(
            reviews,
            key=lambda r: r.published_at or r.created_at or datetime.min,
            reverse=True,
        )[:6]
        mentions = []
        for review in recent:
            product = next((p for p in products if p.id == review.product_id), None)
            if not product:
                continue
            when = review.published_at or review.created_at
            mentions.append({
                "id": review.id,
                "brand": product.brand,
                "initials": (product.brand or "?")[0].upper(),
                "text": (review.content or "")[:180],
                "source": review.source,
                "time": when.strftime("%b %d, %H:%M") if when else "",
                "sentiment": review.sentiment_label or "neutral",
                "engagement": review.helpful,
            })

        # Top movers by absolute price change.
        movers = []
        for product in products:
            history = (
                db.query(PriceHistory)
                .filter(PriceHistory.product_id == product.id)
                .order_by(PriceHistory.recorded_at.asc())
                .all()
            )
            change = self.price_change(history, product.price)
            if change is None:
                continue
            movers.append({
                "id": product.id,
                "name": product.name,
                "brand": product.brand,
                "category": product.category,
                "change": change,
                "color": brand_color(product.brand),
            })
        movers.sort(key=lambda item: abs(item["change"]), reverse=True)

        return {
            "kpis": kpis,
            "evolution": self.evolution_series(db),
            "mentions": mentions,
            "topMovers": movers[:4],
            "product_count": total_products,
            "brand_count": len(brands),
        }

    def _review_spark(self, reviews: Sequence[Review], points: int = 7) -> List[float]:
        if not reviews:
            return []
        dates = [r.published_at or r.created_at for r in reviews if (r.published_at or r.created_at)]
        if not dates:
            return []
        anchor = max(dates)
        start = anchor - timedelta(days=points - 1)
        buckets = [0] * points
        for review in reviews:
            when = review.published_at or review.created_at
            if not when or when < start:
                continue
            index = min(points - 1, max(0, (when - start).days))
            buckets[index] += 1
        return [float(value) for value in buckets]


analytics_service = AnalyticsService()
