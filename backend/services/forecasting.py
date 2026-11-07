import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger("marketpulse.services.forecasting")


class PriceForecastingService:
    """
    Price history analytics and forecasting service.
    Analyzes historical trends, price volatility, and estimates near-term trajectories.
    """

    def analyze_price_history(
        self,
        product_id: int,
        product_name: Optional[str],
        current_price: float,
        price_history: List[Any],
        currency: str = "RON"
    ) -> Dict[str, Any]:
        """
        Computes descriptive price statistics and trend direction.
        """
        prices = [getattr(p, "price", p) for p in price_history if p is not None]

        # Always include the current price in the analysis
        if not prices:
            prices = [current_price]

        min_price = min(prices)
        max_price = max(prices)
        avg_price = sum(prices) / len(prices)

        # Calculate percentage change from the FIRST recorded price to current.
        # `prices` arrives ordered ascending by recorded_at, so the oldest point is
        # index 0. Using [-1] here compared the newest point against itself and
        # always produced ~0 %.
        oldest_price = prices[0] if len(prices) > 1 else current_price
        if oldest_price > 0:
            change_pct = ((current_price - oldest_price) / oldest_price) * 100.0
        else:
            change_pct = 0.0

        return {
            "product_id": product_id,
            "product_name": product_name,
            "current_price": round(current_price, 2),
            "minimum_price": round(min_price, 2),
            "maximum_price": round(max_price, 2),
            "average_price": round(avg_price, 2),
            "currency": currency,
            "price_change_percentage": round(change_pct, 2),
            "history_points": len(prices)
        }

    def forecast_next_period(self, prices: List[float], periods_ahead: int = 7) -> Dict[str, Any]:
        """
        Performs linear projection / simple moving average forecast over time.
        """
        n = len(prices)
        if n < 2:
            current = prices[0] if prices else 0.0
            return {
                "trend": "insufficient_data",
                "projected_price": current,
                "projected_change_pct": 0.0
            }

        # Linear regression slope: y = m*x + b
        x = list(range(n))
        y = prices
        x_mean = sum(x) / n
        y_mean = sum(y) / n

        numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            slope = 0.0
        else:
            slope = numerator / denominator

        intercept = y_mean - (slope * x_mean)
        projected_price = intercept + slope * (n + periods_ahead - 1)
        current = prices[-1]

        if current > 0:
            projected_change_pct = ((projected_price - current) / current) * 100.0
        else:
            projected_change_pct = 0.0

        if slope > 0.05 * (current / n):
            trend = "increasing"
        elif slope < -0.05 * (current / n):
            trend = "decreasing"
        else:
            trend = "stable"

        return {
            "trend": trend,
            "slope": round(slope, 3),
            "projected_price": round(max(projected_price, 0.0), 2),
            "projected_change_pct": round(projected_change_pct, 2)
        }


forecasting_service = PriceForecastingService()
