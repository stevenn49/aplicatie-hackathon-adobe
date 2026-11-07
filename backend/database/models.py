from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Text,
    DateTime,
    ForeignKey,
    JSON,
    Index,
    func
)
from sqlalchemy.orm import relationship
from database.connection import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    brand = Column(String(100), nullable=False, index=True)
    category = Column(String(100), nullable=False, index=True)
    price = Column(Float, nullable=False)
    currency = Column(String(10), default="RON", nullable=False)
    source = Column(String(100), nullable=True)
    source_url = Column(String(1000), nullable=True)
    sku = Column(String(100), nullable=True, index=True, unique=True)
    rating = Column(Float, nullable=True, default=0.0)
    review_count = Column(Integer, default=0)
    specs = Column(JSON, nullable=True)
    # Release label shown in the UI ("Sep 2024"). NULL means "not known".
    launch = Column(String(50), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        server_default=func.now(),
        onupdate=datetime.utcnow
    )

    # Relationships
    price_history = relationship(
        "PriceHistory",
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="PriceHistory.recorded_at.desc()"
    )
    reviews = relationship(
        "Review",
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="Review.created_at.desc()"
    )

    def __repr__(self) -> str:
        return f"<Product(id={self.id}, name='{self.name}', price={self.price} {self.currency})>"


class PriceHistory(Base):
    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    price = Column(Float, nullable=False)
    currency = Column(String(10), default="RON", nullable=False)
    recorded_at = Column(DateTime, default=datetime.utcnow, server_default=func.now(), index=True)

    product = relationship("Product", back_populates="price_history")

    def __repr__(self) -> str:
        return f"<PriceHistory(product_id={self.product_id}, price={self.price}, recorded_at={self.recorded_at})>"


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    source = Column(String(100), nullable=False)  # e.g., 'eMAG', 'Reddit', 'Alternative'
    external_id = Column(String(255), nullable=True)
    author = Column(String(255), nullable=True)
    rating = Column(Float, nullable=True)
    title = Column(String(500), nullable=True)
    content = Column(Text, nullable=False)
    sentiment_score = Column(Float, nullable=True)  # Compound score: -1.0 to 1.0
    sentiment_label = Column(String(50), nullable=True)  # 'positive', 'neutral', 'negative'
    aspects = Column(JSON, nullable=True)  # e.g., {"battery": "positive", "price": "negative"}
    # NULL = the source does not report it. 0 would mean "reported as zero".
    helpful = Column(Integer, nullable=True)
    published_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())

    product = relationship("Product", back_populates="reviews")

    __table_args__ = (
        Index("ix_reviews_product_published", "product_id", "published_at"),
    )

    def __repr__(self) -> str:
        return f"<Review(id={self.id}, product_id={self.product_id}, sentiment='{self.sentiment_label}')>"


class TrendMetric(Base):
    __tablename__ = "trend_metrics"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    category = Column(String(100), nullable=False, index=True)
    keyword = Column(String(255), nullable=False, index=True)
    trend_score = Column(Float, nullable=False)
    search_interest = Column(Float, nullable=False)
    trend_direction = Column(String(50), nullable=False)  # 'increasing', 'stable', 'decreasing'
    source = Column(String(100), default="Google Trends")
    recorded_at = Column(DateTime, default=datetime.utcnow, server_default=func.now(), index=True)

    def __repr__(self) -> str:
        return f"<TrendMetric(category='{self.category}', keyword='{self.keyword}', score={self.trend_score})>"


class LLMCache(Base):
    """
    Cached OpenRouter responses. The free tier allows ~1000 requests/day, so every
    prompt is keyed by a hash of (model, prompt) and reused until it expires.
    """
    __tablename__ = "llm_cache"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    cache_key = Column(String(64), nullable=False, unique=True, index=True)
    model = Column(String(200), nullable=False)
    prompt = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now(), index=True)
    expires_at = Column(DateTime, nullable=True, index=True)

    def __repr__(self) -> str:
        return f"<LLMCache(key='{self.cache_key[:12]}…', model='{self.model}')>"
