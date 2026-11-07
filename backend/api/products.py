import logging
from typing import Optional, List
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from database.connection import get_db, SessionLocal
from database.models import Product as ProductModel, PriceHistory as PriceHistoryModel, Review as ReviewModel
from schemas.product import (
    Product,
    ProductCreate,
    ProductUpdate,
    ProductResponse,
    ProductDetailResponse
)
from schemas.price import PriceHistoryResponse
from schemas.review import ReviewResponse
from schemas.dto import ProductCard, ProductDetail, PricePoint, ProductReviewItem
from services.analytics_service import analytics_service, brand_color
from services.llm_service import llm_service
from data_collection.reviews import review_collector
from data_collection.prices import price_collector
from connectors.emag import emag_connector

logger = logging.getLogger("marketpulse.api.products")

router = APIRouter(
    prefix="/api/products",
    tags=["Products"]
)


def _generate_review_summary(product_name: str, brand: str, stats: dict) -> None:
    """
    Runs after the response is sent. Opens its own session because the request's
    session is already closed by then.
    """
    db = SessionLocal()
    try:
        llm_service.review_summary(product_name, brand, stats, db)
        logger.info(f"Background review summary generated for '{product_name}'")
    except Exception as exc:
        logger.warning(f"Background review summary failed for '{product_name}': {exc}")
    finally:
        db.close()


def _review_stats(reviews: List[ReviewModel]) -> dict:
    """Shared review aggregation used by the card and the drawer."""
    total = len(reviews)
    counts = {"positive": 0, "neutral": 0, "negative": 0}
    score_sum = 0.0
    for review in reviews:
        label = review.sentiment_label or "neutral"
        if label not in counts:
            label = "neutral"
        counts[label] += 1
        score_sum += review.sentiment_score or 0.0
    return {
        "total_reviews": total,
        "positive": round(counts["positive"] / total * 100, 1) if total else 0.0,
        "neutral": round(counts["neutral"] / total * 100, 1) if total else 0.0,
        "negative": round(counts["negative"] / total * 100, 1) if total else 0.0,
        "average_score": round(score_sum / total, 3) if total else 0.0,
    }


def _to_card(product: ProductModel, reviews: List[ReviewModel], history: List[PriceHistoryModel], max_reviews: int) -> ProductCard:
    sentiment = analytics_service.product_sentiment(reviews)
    aspects = analytics_service.aspect_breakdown(reviews)
    pros, cons = analytics_service.pros_cons(aspects)
    return ProductCard(
        id=product.id,
        name=product.name,
        brand=product.brand,
        category=product.category,
        price=round(product.price, 2),
        currency=product.currency or "RON",
        rating=round(product.rating, 2) if product.rating is not None else None,
        review_count=len(reviews) if reviews else (product.review_count or 0),
        sentiment=sentiment,
        change=analytics_service.price_change(history, product.price),
        interest=analytics_service.product_interest(reviews, max_reviews),
        color=brand_color(product.brand),
        launch=product.launch,
        specs=product.specs or {},
        pros=pros,
        cons=cons,
        source=product.source,
        source_url=product.source_url,
    )


def _load_relations(db: Session, product_ids: List[int]):
    """Bulk-load reviews and price history for a set of products."""
    reviews_by_product = {pid: [] for pid in product_ids}
    if product_ids:
        for review in db.query(ReviewModel).filter(ReviewModel.product_id.in_(product_ids)).all():
            reviews_by_product.setdefault(review.product_id, []).append(review)

    history_by_product = {pid: [] for pid in product_ids}
    if product_ids:
        rows = (
            db.query(PriceHistoryModel)
            .filter(PriceHistoryModel.product_id.in_(product_ids))
            .order_by(PriceHistoryModel.recorded_at.asc())
            .all()
        )
        for row in rows:
            history_by_product.setdefault(row.product_id, []).append(row)

    return reviews_by_product, history_by_product


@router.get("/", response_model=List[ProductCard])
def get_products(
    search: Optional[str] = Query(None, description="Search term for name or brand"),
    category: Optional[str] = Query(None, description="Filter by category"),
    brand: Optional[str] = Query(None, description="Filter by brand"),
    min_price: Optional[float] = Query(None, ge=0, description="Minimum price filter"),
    max_price: Optional[float] = Query(None, ge=0, description="Maximum price filter"),
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(100, ge=1, le=500, description="Pagination limit"),
    db: Session = Depends(get_db)
):
    """
    Retrieve and filter tech products, enriched with derived sentiment,
    price movement and aspect-based pros/cons.
    """
    query = db.query(ProductModel)

    if search:
        search_filter = f"%{search.strip()}%"
        query = query.filter(
            or_(
                ProductModel.name.ilike(search_filter),
                ProductModel.brand.ilike(search_filter),
                ProductModel.category.ilike(search_filter)
            )
        )

    if category:
        query = query.filter(ProductModel.category.ilike(category.strip()))

    if brand:
        query = query.filter(ProductModel.brand.ilike(brand.strip()))

    if min_price is not None:
        query = query.filter(ProductModel.price >= min_price)

    if max_price is not None:
        query = query.filter(ProductModel.price <= max_price)

    products = query.order_by(ProductModel.id.asc()).offset(skip).limit(limit).all()
    if not products:
        return []

    ids = [p.id for p in products]
    reviews_by_product, history_by_product = _load_relations(db, ids)

    # Normalise interest against the busiest product in the whole catalogue.
    max_reviews = max(
        (len(v) for v in reviews_by_product.values()),
        default=0,
    )

    return [
        _to_card(
            product,
            reviews_by_product.get(product.id, []),
            history_by_product.get(product.id, []),
            max_reviews,
        )
        for product in products
    ]


@router.get("/compare", response_model=List[ProductCard])
def compare_products(
    ids: str = Query(..., description="Comma-separated product ids, e.g. 1,2,3"),
    db: Session = Depends(get_db)
):
    """
    Return two to four products in the order requested, for the comparison table.
    Unknown ids are skipped rather than failing the whole comparison.
    """
    try:
        parsed = [int(part) for part in ids.split(",") if part.strip()]
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="ids must be a comma-separated list of integers",
        )

    parsed = parsed[:4]
    if len(parsed) < 2:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At least two product ids are required for a comparison",
        )

    products = db.query(ProductModel).filter(ProductModel.id.in_(parsed)).all()
    by_id = {p.id: p for p in products}
    ordered = [by_id[pid] for pid in parsed if pid in by_id]
    if not ordered:
        return []

    reviews_by_product, history_by_product = _load_relations(db, [p.id for p in ordered])
    max_reviews = max((len(v) for v in reviews_by_product.values()), default=0)

    return [
        _to_card(
            product,
            reviews_by_product.get(product.id, []),
            history_by_product.get(product.id, []),
            max_reviews,
        )
        for product in ordered
    ]


@router.get("/{product_id}", response_model=ProductDetail)
def get_product(product_id: int, background: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Full product detail for the drawer: card data, price history, a linear
    forecast, the review list, and an LLM summary when the model is configured.

    The summary is read from the cache only. A reasoning model takes 15-100
    seconds, which would hold the drawer open, so a cache miss returns the
    derived text with `review_summary_source: "pending"` and the generation runs
    in the background; the next request finds it cached.
    """
    product = db.query(ProductModel).filter(ProductModel.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found"
        )

    history = (
        db.query(PriceHistoryModel)
        .filter(PriceHistoryModel.product_id == product.id)
        .order_by(PriceHistoryModel.recorded_at.asc())
        .all()
    )
    reviews = (
        db.query(ReviewModel)
        .filter(ReviewModel.product_id == product.id)
        .order_by(ReviewModel.published_at.desc())
        .all()
    )

    max_reviews = max(
        (db.query(ReviewModel).filter(ReviewModel.product_id == pid).count()
         for (pid,) in db.query(ProductModel.id).all()),
        default=0,
    )
    card = _to_card(product, reviews, history, max_reviews)

    price_points = [
        PricePoint(date=row.recorded_at.strftime("%b %d"), price=round(row.price, 2))
        for row in history
    ]

    # Linear projection from the stored points, not a fabricated curve.
    forecast: List[PricePoint] = []
    if len(history) >= 2:
        from services.forecasting import forecasting_service
        prices = [row.price for row in history]
        projection = forecasting_service.forecast_next_period(prices, periods_ahead=30)
        last_date = history[-1].recorded_at
        from datetime import timedelta
        forecast = [
            PricePoint(date=(last_date + timedelta(days=30)).strftime("%b %d"), price=projection["projected_price"])
        ]

    review_items = [
        ProductReviewItem(
            id=review.id,
            author=review.author or "Anonymous",
            rating=review.rating,
            title=review.title,
            text=review.content,
            sentiment=review.sentiment_label or "neutral",
            sentiment_score=review.sentiment_score,
            source=review.source,
            date=(review.published_at or review.created_at).strftime("%b %d, %Y")
            if (review.published_at or review.created_at) else "",
            aspects=review.aspects or {},
        )
        for review in reviews[:20]
    ]

    stats = _review_stats(reviews)
    stats["aspects"] = {
        name: data["score"] for name, data in analytics_service.aspect_breakdown(reviews).items()
    }

    summary = llm_service.review_summary(
        product.name, product.brand, stats, db, cache_only=True
    )

    if summary:
        summary_source = "llm"
    elif llm_service.enabled and reviews:
        # Not cached yet: generate it in the background so the drawer opens now.
        background.add_task(_generate_review_summary, product.name, product.brand, stats)
        summary_source = "pending"
    else:
        summary_source = "unavailable"

    return ProductDetail(
        product=card,
        price_history=price_points,
        forecast=forecast,
        reviews=review_items,
        review_summary=summary,
        review_summary_source=summary_source,
    )


@router.get("/{product_id}/detail", response_model=ProductDetailResponse)
def get_product_detail(product_id: int, db: Session = Depends(get_db)):
    """
    Raw ORM detail (price history + reviews) kept for backwards compatibility
    with the original backend contract.
    """
    product = db.query(ProductModel).filter(ProductModel.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found"
        )
    return product


@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(product_data: ProductCreate, db: Session = Depends(get_db)):
    """
    Create a new product and register its initial price record.
    """
    product_dict = product_data.model_dump()
    new_product = ProductModel(**product_dict)

    db.add(new_product)
    db.commit()
    db.refresh(new_product)

    db.add(PriceHistoryModel(
        product_id=new_product.id,
        price=new_product.price,
        currency=new_product.currency
    ))
    db.commit()
    db.refresh(new_product)

    logger.info(f"Created product: '{new_product.name}' (ID: {new_product.id})")
    return new_product


@router.post(
    "/import-from-emag",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED
)
def import_product_from_emag(
    query: str = Query(..., min_length=2, description="Product search term (e.g. 'iPhone 15', 'RTX 4070')"),
    category: Optional[str] = Query(None, description="Override category (defaults to auto-detected or Technology)"),
    db: Session = Depends(get_db)
):
    """
    Searches the eMAG public catalogue live and registers the best match.
    Returns 503 with an explicit reason when eMAG cannot be reached — it never
    fabricates a product.
    """
    results = emag_connector.search_products(query, limit=5)
    if not results:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                f"eMAG returned no parseable results for '{query}'. "
                "The public catalogue may be rate-limiting this IP or the page layout changed."
            )
        )

    best = results[0]
    detected_cat = category or ("Smartphone" if "telefon" in best["name"].lower() or "iphone" in best["name"].lower() or "galaxy" in best["name"].lower() else "Technology")

    new_product = ProductModel(
        name=best["name"],
        brand=best["brand"],
        category=detected_cat,
        price=best["price"],
        currency=best.get("currency", "RON"),
        source="eMAG",
        source_url=best.get("source_url"),
        rating=best.get("rating", 0.0),
        review_count=best.get("review_count", 0)
    )

    db.add(new_product)
    db.commit()
    db.refresh(new_product)

    db.add(PriceHistoryModel(
        product_id=new_product.id,
        price=new_product.price,
        currency=new_product.currency
    ))
    db.commit()
    db.refresh(new_product)

    logger.info(f"Imported real product from eMAG: '{new_product.name}' (ID: {new_product.id}, Price: {new_product.price} {new_product.currency})")
    return new_product


@router.put("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int,
    update_data: ProductUpdate,
    db: Session = Depends(get_db)
):
    """
    Update an existing product's attributes.
    If the price changes, a new record is added to price_history.
    """
    product = db.query(ProductModel).filter(ProductModel.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found"
        )

    update_dict = update_data.model_dump(exclude_unset=True)

    new_price = update_dict.get("price")
    if new_price is not None and new_price != product.price:
        db.add(PriceHistoryModel(
            product_id=product.id,
            price=new_price,
            currency=update_dict.get("currency", product.currency)
        ))

    for field, val in update_dict.items():
        setattr(product, field, val)

    db.commit()
    db.refresh(product)
    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    """
    Delete a product and cascade delete all its reviews and price records.
    """
    product = db.query(ProductModel).filter(ProductModel.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found"
        )
    db.delete(product)
    db.commit()
    return None


@router.get("/{product_id}/prices", response_model=List[PriceHistoryResponse])
def get_product_prices(product_id: int, db: Session = Depends(get_db)):
    """
    List all historical price points recorded for a given product.
    """
    product = db.query(ProductModel).filter(ProductModel.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found"
        )
    return product.price_history


@router.get("/{product_id}/reviews", response_model=List[ReviewResponse])
def get_product_reviews(product_id: int, db: Session = Depends(get_db)):
    """
    List all customer reviews and feedback associated with a product.
    """
    product = db.query(ProductModel).filter(ProductModel.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found"
        )
    return product.reviews


@router.post("/{product_id}/collect-reviews")
def trigger_review_collection(
    product_id: int,
    sources: Optional[List[str]] = Query(None, description="Sources: alternative, reddit, emag, twitter"),
    limit_per_source: int = Query(5, ge=1, le=25),
    db: Session = Depends(get_db)
):
    """
    Trigger on-demand collection, sentiment analysis, and deduplication of reviews
    for this product across configured external connectors.
    """
    product = db.query(ProductModel).filter(ProductModel.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found"
        )

    summary = review_collector.collect_for_product(
        product=product,
        db=db,
        sources=sources,
        limit_per_source=limit_per_source
    )
    return summary


@router.post("/{product_id}/sync-price")
def trigger_price_sync(product_id: int, db: Session = Depends(get_db)):
    """
    Poll live market price from external catalog and record a new price point if changed.
    """
    product = db.query(ProductModel).filter(ProductModel.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found"
        )

    return price_collector.update_product_price(product, db)
