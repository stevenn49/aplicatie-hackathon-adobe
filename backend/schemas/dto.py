"""
Data-transfer objects for the React dashboard.

These are the exact shapes `src/services/api.js` consumes. They are deliberately
separate from the ORM models: the pages need presentation values (sentiment on a
0-100 scale, a brand colour, a price delta) that are derived from stored rows and
must never be invented.

Rule used throughout: a value that cannot be computed from stored data is `None`,
and the UI renders "not enough data". A fabricated zero is never returned.
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


# --------------------------------------------------------------------------- #
# Products
# --------------------------------------------------------------------------- #

class ProductCard(BaseModel):
    """One row in the Product Analysis table and one bubble in the comparison."""
    id: int
    name: str
    brand: str
    category: str
    price: float
    currency: str = "RON"
    rating: Optional[float] = None
    review_count: int = 0
    sentiment: Optional[float] = None          # 0-100, None when no reviews
    change: Optional[float] = None             # % price movement, None when <2 points
    interest: Optional[float] = None           # 0-100 mention intensity, None when no reviews
    color: str                                 # stable per-brand colour
    launch: Optional[str] = None               # "Sep 2024" or None
    specs: Dict[str, Any] = {}
    pros: List[str] = []
    cons: List[str] = []
    source: Optional[str] = None
    source_url: Optional[str] = None


class PricePoint(BaseModel):
    date: str
    price: float


class ProductReviewItem(BaseModel):
    id: int
    author: str
    rating: Optional[float] = None
    title: Optional[str] = None
    text: str
    sentiment: str
    sentiment_score: Optional[float] = None
    source: str
    date: str
    aspects: Dict[str, Any] = {}


class ProductDetail(BaseModel):
    """The drawer in Product Analysis."""
    product: ProductCard
    price_history: List[PricePoint] = []
    forecast: List[PricePoint] = []
    reviews: List[ProductReviewItem] = []
    review_summary: Optional[str] = None       # LLM text, None when the LLM is off
    review_summary_source: str = "unavailable"  # "llm" | "pending" | "unavailable"


# --------------------------------------------------------------------------- #
# Market overview
# --------------------------------------------------------------------------- #

class Kpi(BaseModel):
    label: str
    value: str
    suffix: Optional[str] = None
    change: Optional[str] = None
    note: Optional[str] = None
    tone: str = "neutral"                      # "positive" | "negative" | "neutral"
    icon: str = "trend"                        # layers | message | heart | trend
    spark: List[float] = []


class EvolutionPoint(BaseModel):
    month: str
    Apple: Optional[float] = None
    NVIDIA: Optional[float] = None
    Microsoft: Optional[float] = None
    Samsung: Optional[float] = None
    Sony: Optional[float] = None


class Mention(BaseModel):
    id: int
    brand: str
    initials: str
    text: str
    source: str
    time: str
    sentiment: str
    engagement: Optional[int] = None           # None when the source does not report it


class TopMover(BaseModel):
    id: int
    name: str
    brand: str
    category: str
    change: Optional[float] = None
    color: str


class MarketOverview(BaseModel):
    kpis: List[Kpi] = []
    evolution: List[EvolutionPoint] = []
    mentions: List[Mention] = []
    topMovers: List[TopMover] = []
    product_count: int = 0
    brand_count: int = 0


# --------------------------------------------------------------------------- #
# Sentiment
# --------------------------------------------------------------------------- #

class SentimentSlice(BaseModel):
    name: str
    value: float
    color: str


class SentimentTrendPoint(BaseModel):
    date: str
    positive: float
    neutral: float
    negative: float


class AspectScore(BaseModel):
    aspect: str
    score: float                               # 0-100
    mentions: int = 0


class KeywordItem(BaseModel):
    word: str
    score: float                               # 0-100
    tone: str                                  # positive | neutral | negative


class ReviewItem(BaseModel):
    id: int
    author: str
    brand: str
    product: str
    text: str
    rating: Optional[float] = None
    sentiment: str
    source: str
    date: str
    helpful: Optional[int] = None


class SentimentDashboard(BaseModel):
    distribution: List[SentimentSlice] = []
    trend: List[SentimentTrendPoint] = []
    aspects: List[AspectScore] = []
    keywords: List[KeywordItem] = []
    reviews: List[ReviewItem] = []
    total_reviews: int = 0


# --------------------------------------------------------------------------- #
# Brands
# --------------------------------------------------------------------------- #

class BrandStat(BaseModel):
    brand: str
    color: str
    shareOfVoice: float
    mentions: int
    sentiment: Optional[float] = None          # 0-100
    health: Optional[float] = None             # 0-100 composite
    topics: List[str] = []                     # most praised aspects
    concerns: List[str] = []                   # most criticised aspects


# --------------------------------------------------------------------------- #
# Consumer segments
# --------------------------------------------------------------------------- #

class ConsumerSegment(BaseModel):
    id: str
    name: str
    size: str                                  # "28%"
    sizeValue: float                           # 28.0
    users: str                                 # "23.6k"
    usersValue: int
    spend: str                                 # "1,240 lei"
    spendValue: float
    loyalty: float                             # 0-100
    sensitivity: float                         # 0-100
    preferences: List[str] = []
    color: str


# --------------------------------------------------------------------------- #
# Marketing
# --------------------------------------------------------------------------- #

class MarketingTrendPoint(BaseModel):
    date: str
    Apple: Optional[float] = None
    NVIDIA: Optional[float] = None
    Microsoft: Optional[float] = None
    Samsung: Optional[float] = None
    Sony: Optional[float] = None
    Reddit: Optional[float] = None
    X: Optional[float] = None
    event: Optional[str] = None


class MarketingOpportunity(BaseModel):
    title: str
    type: str
    detail: str
    impact: str
    color: str


class MarketingDashboard(BaseModel):
    trends: List[MarketingTrendPoint] = []
    opportunities: List[MarketingOpportunity] = []
    opportunities_source: str = "derived"      # "llm" | "pending" | "derived"
    kpis: List[Kpi] = []
    source_volume: List[Dict[str, Any]] = []


# --------------------------------------------------------------------------- #
# Competitors
# --------------------------------------------------------------------------- #

class CompetitorBrand(BaseModel):
    name: str
    color: str
    share: float
    health: Optional[float] = None


class PriceDifference(BaseModel):
    name: str
    brand: str
    price: float
    baseline: float
    difference: float


class FeatureRow(BaseModel):
    brand: str
    values: List[Optional[float]]


class CompetitorDashboard(BaseModel):
    brands: List[CompetitorBrand] = []
    priceDifferences: List[PriceDifference] = []
    features: List[str] = []
    matrix: List[FeatureRow] = []
    activity: List[Dict[str, Any]] = []


# --------------------------------------------------------------------------- #
# Recommendations
# --------------------------------------------------------------------------- #

class InsightCard(BaseModel):
    id: str
    category: str                              # Product | Consumer | Marketing | Competitive
    priority: str                              # High | Medium | Low
    title: str
    detail: str
    metric: str
    confidence: int                            # 0-100
    related: str                               # "Brand · Product"
    route: str                                 # "/products"
    icon: str                                  # target | sparkles | users | swords | headphones


class ExecutiveSummary(BaseModel):
    headline: str
    body: str
    source: str = "derived"                    # "llm" | "pending" | "derived"
    readiness: Optional[float] = None          # 0-100
    avg_confidence: Optional[float] = None


class RecommendationsDashboard(BaseModel):
    summary: ExecutiveSummary
    items: List[InsightCard] = []
    high_priority: int = 0
