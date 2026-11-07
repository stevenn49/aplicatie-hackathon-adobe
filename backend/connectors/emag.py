import re
import urllib.parse
import logging
from typing import List, Dict, Any, Optional, Tuple
from bs4 import BeautifulSoup

from connectors.base import BaseConnector
from config import settings

logger = logging.getLogger("marketpulse.connectors.emag")


class EmagConnector(BaseConnector):
    """
    Public web connector for eMAG marketplace data.
    Extracts public product listings, current prices, ratings, and customer reviews
    without requiring private Seller API credentials.
    """

    def __init__(self):
        super().__init__(
            name="eMAG",
            rate_limit_delay=settings.EMAG_RATE_LIMIT_DELAY,
            timeout=settings.EMAG_REQUEST_TIMEOUT
        )
        self.base_url = "https://www.emag.ro"

    def search_products(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Searches eMAG catalog for tech products matching the query.
        Returns a list of standardized product dictionaries.
        """
        encoded_query = urllib.parse.quote(query.strip())
        search_url = f"{self.base_url}/search/{encoded_query}"

        logger.info(f"[eMAG] Searching public catalog for: '{query}' ({search_url})")
        response = self.fetch_get(search_url)

        if not response:
            logger.warning(f"[eMAG] Failed to fetch catalog results for query '{query}'")
            return []

        return self._parse_catalog_html(response.text, limit)

    def _parse_catalog_html(self, html_content: str, limit: int) -> List[Dict[str, Any]]:
        """
        Parses HTML product cards from eMAG search results page.
        """
        soup = BeautifulSoup(html_content, "html.parser")
        items: List[Dict[str, Any]] = []

        # eMAG product card selectors
        product_cards = soup.select(".card-item, .card-v2, [data-card-type='product']")

        for card in product_cards:
            if len(items) >= limit:
                break

            try:
                # 1. Product Title & URL
                title_elem = card.select_one("a.card-v2-title, .card-v2-title-wrapper, a.product-title")
                link_elem = card.select_one("a.js-product-url, a.card-v2-title, a[href*='/pd/']")
                if not title_elem and not link_elem:
                    continue

                name = (title_elem or link_elem).get_text(strip=True)
                url = (link_elem or title_elem).get("href", "")
                if url and not url.startswith("http"):
                    url = urllib.parse.urljoin(self.base_url, url)

                # 2. Price Parsing
                price_elem = card.select_one(".product-new-price, p.product-new-price")
                if not price_elem:
                    continue

                price_text = price_elem.get_text(separator=" ", strip=True)
                price_val, currency = self._clean_price(price_text)

                if not price_val:
                    continue

                # 3. Rating & Review Count
                rating = 0.0
                reviews_count = 0
                rating_container = card.select_one(".star-rating-container, .star-rating-text, .average-rating")
                if rating_container:
                    rc_text = rating_container.get_text(separator=" ", strip=True)
                    # Rating e.g. 4.69
                    rm = re.search(r"(\d+[\.,]\d+)", rc_text)
                    if rm:
                        rating = float(rm.group(1).replace(",", "."))
                    # Reviews count e.g. (646) or 646 de review-uri
                    cm = re.search(r"\((\d+)\)", rc_text) or re.search(r"(\d+)\s*(?:de\s+)?(?:review|recenzii)", rc_text, re.IGNORECASE)
                    if cm:
                        reviews_count = int(cm.group(1))

                # 4. Brand deduction
                brand = self._infer_brand(name)

                items.append({
                    "name": name,
                    "brand": brand,
                    "price": price_val,
                    "currency": currency or "RON",
                    "rating": rating or 0.0,
                    "review_count": reviews_count,
                    "source": "eMAG",
                    "source_url": url
                })
            except Exception as e:
                logger.debug(f"[eMAG] Skipping malformed card: {e}")
                continue

        logger.info(f"[eMAG] Extracted {len(items)} products from catalog.")
        return items

    def fetch_product_reviews(self, product_url: str, max_reviews: int = 15) -> List[Dict[str, Any]]:
        """
        Parses publicly posted user reviews from an eMAG product details page.
        """
        logger.info(f"[eMAG] Fetching public reviews for: {product_url}")
        response = self.fetch_get(product_url)
        if not response:
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        review_elements = soup.select(".product-review, .review-item, [class*='review-item-']")
        reviews: List[Dict[str, Any]] = []

        for rev in review_elements:
            if len(reviews) >= max_reviews:
                break

            try:
                content_elem = rev.select_one(".review-body, .product-review-body, [class*='review-content']")
                if not content_elem:
                    continue
                content = content_elem.get_text(strip=True)

                title_elem = rev.select_one(".review-title, .product-review-title, h4")
                title = title_elem.get_text(strip=True) if title_elem else None

                author_elem = rev.select_one(".review-author, .user-name, [class*='author']")
                author = author_elem.get_text(strip=True) if author_elem else "Client eMAG"

                # Rating (1-5 stars)
                star_elem = rev.select_one(".star-rating, [class*='star-rating-']")
                rating = 5.0
                if star_elem:
                    match = re.search(r"(\d+)", star_elem.get("class", [""])[0] if isinstance(star_elem.get("class"), list) else "")
                    if match:
                        rating = float(match.group(1))

                reviews.append({
                    "author": author,
                    "rating": rating,
                    "title": title,
                    "content": content,
                    "source": "eMAG"
                })
            except Exception as e:
                logger.debug(f"[eMAG] Error parsing review: {e}")
                continue

        return reviews

    def _clean_price(self, price_raw: str) -> Tuple[Optional[float], str]:
        """
        Normalizes Romanian eMAG price formats such as:
            '3.999,99 Lei'  -> (3999.99, 'RON')
            '899,00 lei'    -> (899.0,   'RON')
            '2 499 RON'     -> (2499.0,  'RON')   (space thousands separator)
            '1.234,5 Lei'   -> (1234.5,  'RON')

        The previous version only stripped dots, so a price written with a space
        as the thousands separator ('2 499 RON') parsed as 2.0 and the product
        was recorded at the wrong price.
        """
        if not price_raw:
            return None, "RON"

        clean = re.sub(r"(?i)\b(lei|ron)\b", "", price_raw)
        # Drop every space, including the non-breaking space eMAG uses.
        clean = clean.replace(" ", "").replace(" ", "").replace(" ", "").strip()

        if not clean:
            return None, "RON"

        has_comma = "," in clean
        has_dot = "." in clean

        if has_comma and has_dot:
            # 3.999,99 -> dots are thousands, comma is the decimal mark
            clean = clean.replace(".", "").replace(",", ".")
        elif has_comma:
            # 899,00 -> comma is the decimal mark
            clean = clean.replace(",", ".")
        elif has_dot:
            # A single dot is ambiguous. Three digits after the last dot means a
            # thousands separator (3.999); anything else is a decimal mark.
            head, _, tail = clean.rpartition(".")
            if len(tail) == 3 and head.isdigit():
                clean = clean.replace(".", "")
            # else: keep the dot as the decimal mark

        match = re.search(r"(\d+(?:\.\d+)?)", clean)
        if match:
            try:
                return float(match.group(1)), "RON"
            except ValueError:
                return None, "RON"
        return None, "RON"

    def _infer_brand(self, title: str) -> str:
        """
        Identifies prominent tech brand from product title.
        """
        known_brands = [
            "Apple", "Samsung", "Sony", "NVIDIA", "Microsoft", "Asus", "Lenovo",
            "Dell", "HP", "Xiaomi", "Google", "OnePlus", "Huawei", "Intel", "AMD",
            "Logitech", "LG", "Bose", "Motorola"
        ]
        title_lower = title.lower()
        for b in known_brands:
            if b.lower() in title_lower:
                return b
        return "Generic"


emag_connector = EmagConnector()
