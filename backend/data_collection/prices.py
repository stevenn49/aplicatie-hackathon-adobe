import logging
from typing import Dict, Any, List
from datetime import datetime
from sqlalchemy.orm import Session

from database.models import Product, PriceHistory
from connectors.emag import emag_connector

logger = logging.getLogger("marketpulse.data_collection.prices")


class PriceCollector:
    """
    Price monitoring and historical tracking collector.
    Polls connectors for current retail prices and records price milestones.
    """

    def __init__(self):
        self.emag = emag_connector

    def update_product_price(self, product: Product, db: Session) -> Dict[str, Any]:
        """
        Polls connectors for the latest market price of a specific product.
        Appends to price history if price changes or updates the latest timestamp.
        """
        logger.info(f"[PriceCollector] Checking live price for: '{product.name}' (Current: {product.price} {product.currency})")

        # Search product in eMAG catalog
        results = self.emag.search_products(product.name, limit=3)
        if not results:
            return {
                "product_id": product.id,
                "status": "no_results_found",
                "current_price": product.price
            }

        # Select closest matching product from results
        best_match = results[0]
        observed_price = best_match.get("price")
        observed_currency = best_match.get("currency", "RON")

        if not observed_price:
            return {
                "product_id": product.id,
                "status": "invalid_price_format",
                "current_price": product.price
            }

        price_changed = abs(observed_price - product.price) > 0.01

        if price_changed:
            # Capture the previous price BEFORE reassigning it: the old code read
            # product.price after the assignment, so old_price always equalled
            # new_price in the response.
            previous_price = product.price
            logger.info(f"[PriceCollector] Price change detected for '{product.name}': {previous_price} -> {observed_price} {observed_currency}")
            product.price = observed_price
            product.currency = observed_currency
            product.updated_at = datetime.utcnow()

            # Record new point in price history
            history_entry = PriceHistory(
                product_id=product.id,
                price=observed_price,
                currency=observed_currency,
                recorded_at=datetime.utcnow()
            )
            db.add(history_entry)
            db.commit()

            return {
                "product_id": product.id,
                "status": "price_updated",
                "old_price": previous_price,
                "new_price": observed_price,
                "currency": observed_currency
            }
        else:
            return {
                "product_id": product.id,
                "status": "price_unchanged",
                "current_price": product.price
            }

    def sync_all_products(self, db: Session) -> List[Dict[str, Any]]:
        """
        Runs price synchronization across all registered products in the database.
        """
        products = db.query(Product).all()
        results = []
        for p in products:
            res = self.update_product_price(p, db)
            results.append(res)
        return results


price_collector = PriceCollector()
