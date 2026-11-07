import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from connectors.base import BaseConnector

logger = logging.getLogger("marketpulse.connectors.google_trends")


class GoogleTrendsConnector(BaseConnector):
    """
    Google Trends Connector.
    Measures search interest, consumer demand momentum, and trend directions
    for technology brands, products, and market segments.
    """

    def __init__(self):
        super().__init__(name="GoogleTrends", rate_limit_delay=2.5, timeout=20)
        self._pytrends = None
        self._init_pytrends()

    def _init_pytrends(self):
        try:
            from pytrends.request import TrendReq
            self._pytrends = TrendReq(hl="en-US", tz=120, timeout=(10, 25))
            logger.info("[GoogleTrends] PyTrends client initialized successfully.")
        except Exception as e:
            logger.warning(f"[GoogleTrends] PyTrends could not be initialized: {e}")
            self._pytrends = None

    def search_products(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        return self.get_interest(query)

    def get_interest(self, keyword: str, category_name: str = "Technology") -> List[Dict[str, Any]]:
        """
        Retrieves search interest over time for a keyword.
        Returns normalized trend score and direction.
        """
        logger.info(f"[GoogleTrends] Analyzing search interest for: '{keyword}'")

        if self._pytrends:
            try:
                self._apply_rate_limit()
                self._pytrends.build_payload(kw_list=[keyword], timeframe="today 3-m")
                df = self._pytrends.interest_over_time()

                if not df.empty and keyword in df.columns:
                    series = df[keyword].tolist()
                    if series:
                        recent_interest = float(series[-1])
                        avg_interest = float(sum(series) / len(series))

                        # Determine direction from last 4 periods vs earlier average
                        last_window = series[-4:] if len(series) >= 4 else series
                        window_avg = sum(last_window) / len(last_window)

                        if window_avg > avg_interest * 1.05:
                            direction = "increasing"
                        elif window_avg < avg_interest * 0.95:
                            direction = "decreasing"
                        else:
                            direction = "stable"

                        return [{
                            "category": category_name,
                            "keyword": keyword,
                            "trend_score": round(recent_interest, 1),
                            "search_interest": round(avg_interest, 1),
                            "trend_direction": direction,
                            "source": "Google Trends",
                            "recorded_at": datetime.utcnow()
                        }]
            except Exception as exc:
                logger.warning(
                    f"[GoogleTrends] PyTrends query rate-limited or failed for '{keyword}': {exc}"
                )

        # No fabricated fallback. The previous implementation returned a hardcoded
        # 88.0 / 72.0 score labelled "MarketPulse Trend Engine", which presented an
        # invented number as a measurement. An empty list means "not measured" and
        # the API layer reports it as unavailable.
        logger.info(f"[GoogleTrends] No live data available for '{keyword}'.")
        return []


google_trends_connector = GoogleTrendsConnector()
