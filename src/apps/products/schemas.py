from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime


# Base Product schema
class ProductBase(BaseModel):
    article_number: str = Field(..., description="Unique article number")
    product: str = Field(..., description="Product name")
    in_price: float = Field(..., ge=0, description="Purchase/cost price")
    price: float = Field(..., ge=0, description="Selling price")
    unit: str = Field(..., description="Unit of measurement (kg, pieces, liters, etc.)")
    stock: int = Field(default=0, ge=0, description="Stock quantity")
    description: Optional[str] = Field(None, description="Product description")


# Product creation schema
class ProductCreate(ProductBase):
    pass


# Product update schema (all fields optional for partial updates)
class ProductUpdate(BaseModel):
    article_number: Optional[str] = Field(None, description="Unique article number")
    product: Optional[str] = Field(None, description="Product name")
    in_price: Optional[float] = Field(None, ge=0, description="Purchase/cost price")
    price: Optional[float] = Field(None, ge=0, description="Selling price")
    unit: Optional[str] = Field(None, description="Unit of measurement")
    stock: Optional[int] = Field(None, ge=0, description="Stock quantity")
    description: Optional[str] = Field(None, description="Product description")


# Product response schema
class ProductResponse(ProductBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Product list response with pagination info
class ProductListResponse(BaseModel):
    products: list[ProductResponse]
    total: int
    page: int
    size: int
    pages: int


# Stock update schema
class StockUpdate(BaseModel):
    stock: int = Field(..., ge=0, description="New stock quantity")


# Price update schema
class PriceUpdate(BaseModel):
    in_price: Optional[float] = Field(None, ge=0, description="Purchase/cost price")
    price: Optional[float] = Field(None, ge=0, description="Selling price")


# Search/filter schema
class ProductFilter(BaseModel):
    search: Optional[str] = Field(None, description="Search in product name or article number")
    min_price: Optional[float] = Field(None, ge=0, description="Minimum price filter")
    max_price: Optional[float] = Field(None, ge=0, description="Maximum price filter")
    unit: Optional[str] = Field(None, description="Filter by unit")
    low_stock: Optional[bool] = Field(None, description="Filter products with low stock (< 10)")


# Response schemas
class MessageResponse(BaseModel):
    message: str