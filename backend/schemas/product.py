from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, ConfigDict, Field
from schemas.price import PriceHistoryResponse
from schemas.review import ReviewResponse


class ProductBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=150, description="Product full name")
    brand: str = Field(..., description="Brand name e.g. Apple, Samsung, Sony")
    category: str = Field(..., description="Product category e.g. Smartphone, Laptop, Headphones")
    price: float = Field(..., gt=0, description="Current product price")
    currency: str = Field(default="RON", description="Currency code")
    source: Optional[str] = Field(default=None, description="Data source e.g. eMAG, Manual")
    source_url: Optional[str] = Field(default=None, description="Direct URL to product page")
    sku: Optional[str] = Field(default=None, description="Stock keeping unit or model code")
    specs: Optional[Dict[str, Any]] = Field(default=None, description="Technical specifications")
    launch: Optional[str] = Field(default=None, description="Release label shown in the UI, e.g. 'Sep 2024'")


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=150)
    brand: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = Field(None, gt=0)
    currency: Optional[str] = None
    source: Optional[str] = None
    source_url: Optional[str] = None
    sku: Optional[str] = None
    specs: Optional[Dict[str, Any]] = None
    launch: Optional[str] = None


class ProductResponse(ProductBase):
    id: int
    rating: Optional[float] = Field(default=0.0)
    review_count: Optional[int] = Field(default=0)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# Alias for backward compatibility with existing code
Product = ProductResponse


class ProductDetailResponse(ProductResponse):
    price_history: List[PriceHistoryResponse] = []
    reviews: List[ReviewResponse] = []

    model_config = ConfigDict(from_attributes=True)
