import logging
from typing import List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

from database.models import TrendMetric
from connectors.google_trends import google_trends_connector

logger = logging.getLogger("marketpulse.data_collection.trends")


class TrendCollector:
    """
    Market trend collection pipeline.
    Periodically refreshes interest indices across defined tech categories.
    """

    def __init__(self):
        self.default_tracked_topics = [
            {"category": "Smartphone", "keyword": "Samsung Galaxy vs iPhone"},
            {"category": "Laptop", "keyword": "Apple MacBook M4 vs Copilot PC"},
            {"category": "Graphics Card", "keyword": "NVIDIA GeForce RTX 5080"},
            {"category": "Headphones", "keyword": "Sony WH-1000XM5 Noise Cancelling"},
        ]

    def refresh_trends(self, db: Session) -> List[Dict[str, Any]]:
        """
        Polls Google Trends connector for tracked technology topics and updates DB.
        """
        logger.info("[TrendCollector] Starting refresh of technology market trends...")
        updated_records = []

        unavailable = []

        for item in self.default_tracked_topics:
            category = item["category"]
            keyword = item["keyword"]

            trend_data_list = google_trends_connector.get_interest(keyword, category_name=category)
            if not trend_data_list:
                # The connector no longer fabricates a score. Record the gap so the
                # caller can report it instead of silently showing stale numbers.
                unavailable.append(keyword)
                continue

            for t in trend_data_list:
                # Check if existing metric for category & keyword exists
                existing = (
                    db.query(TrendMetric)
                    .filter(TrendMetric.category == category, TrendMetric.keyword == keyword)
                    .first()
                )

                if existing:
                    existing.trend_score = t["trend_score"]
                    existing.search_interest = t["search_interest"]
                    existing.trend_direction = t["trend_direction"]
                    existing.recorded_at = datetime.utcnow()
                else:
                    new_metric = TrendMetric(
                        category=category,
                        keyword=keyword,
                        trend_score=t["trend_score"],
                        search_interest=t["search_interest"],
                        trend_direction=t["trend_direction"],
                        source=t.get("source", "Google Trends"),
                        recorded_at=datetime.utcnow()
                    )
                    db.add(new_metric)

                updated_records.append(t)

        db.commit()
        if unavailable:
            logger.warning(
                f"[TrendCollector] Google Trends returned nothing for: {', '.join(unavailable)}. "
                "Those metrics were left unchanged."
            )
        logger.info(f"[TrendCollector] Successfully refreshed {len(updated_records)} trend metrics.")
        return updated_records


trend_collector = TrendCollector()
