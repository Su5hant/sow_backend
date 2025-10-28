from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
import math

from core.database import get_db
from apps.auth.routes import get_current_user
from apps.auth.models import User
from apps.products.models import Product
from apps.products.schemas import (
    ProductCreate, ProductUpdate, ProductResponse, ProductListResponse,
    StockUpdate, PriceUpdate, ProductFilter, MessageResponse
)

products_router = APIRouter()


@products_router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    product_data: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new product."""
    # Check if article number already exists
    existing_product = db.query(Product).filter(Product.article_number == product_data.article_number).first()
    if existing_product:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Product with article number '{product_data.article_number}' already exists"
        )
    
    # Create new product
    product = Product(**product_data.dict())
    db.add(product)
    db.commit()
    db.refresh(product)
    
    return ProductResponse.model_validate(product)


@products_router.get("/", response_model=ProductListResponse)
async def get_products(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size"),
    search: Optional[str] = Query(None, description="Search in product name or article number"),
    min_price: Optional[float] = Query(None, ge=0, description="Minimum price filter"),
    max_price: Optional[float] = Query(None, ge=0, description="Maximum price filter"),
    unit: Optional[str] = Query(None, description="Filter by unit"),
    low_stock: Optional[bool] = Query(None, description="Filter products with low stock (< 10)"),
    db: Session = Depends(get_db)
):
    """Get products with pagination and filtering."""
    query = db.query(Product)
    
    # Apply filters
    if search:
        query = query.filter(
            or_(
                Product.product.ilike(f"%{search}%"),
                Product.article_number.ilike(f"%{search}%"),
                Product.description.ilike(f"%{search}%")
            )
        )
    
    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    
    if max_price is not None:
        query = query.filter(Product.price <= max_price)
    
    if unit:
        query = query.filter(Product.unit.ilike(f"%{unit}%"))
    
    if low_stock:
        query = query.filter(Product.stock < 10)
    
    # Get total count
    total = query.count()
    query = query.order_by(Product.product.asc())
    
    # Apply pagination
    offset = (page - 1) * size
    products = query.offset(offset).limit(size).all()
    
    # Calculate pagination info
    pages = math.ceil(total / size)
    
    return ProductListResponse(
        products=[ProductResponse.model_validate(product) for product in products],
        total=total,
        page=page,
        size=size,
        pages=pages
    )


@products_router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific product by ID."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    return ProductResponse.model_validate(product)


@products_router.get("/article/{article_number}", response_model=ProductResponse)
async def get_product_by_article_number(
    article_number: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific product by article number."""
    product = db.query(Product).filter(Product.article_number == article_number).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with article number '{article_number}' not found"
        )
    
    return ProductResponse.model_validate(product)


@products_router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    product_data: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a product."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    # Check if article number is being updated and if it already exists
    if product_data.article_number and product_data.article_number != product.article_number:
        existing_product = db.query(Product).filter(
            Product.article_number == product_data.article_number
        ).first()
        if existing_product:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Product with article number '{product_data.article_number}' already exists"
            )
    
    # Update product fields
    update_data = product_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)
    
    db.commit()
    db.refresh(product)
    
    return ProductResponse.model_validate(product)


@products_router.patch("/{product_id}/stock", response_model=ProductResponse)
async def update_product_stock(
    product_id: int,
    stock_data: StockUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update product stock quantity."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    product.stock = stock_data.stock
    db.commit()
    db.refresh(product)
    
    return ProductResponse.model_validate(product)


@products_router.patch("/{product_id}/price", response_model=ProductResponse)
async def update_product_price(
    product_id: int,
    price_data: PriceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update product prices."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    if price_data.in_price is not None:
        product.in_price = price_data.in_price
    
    if price_data.price is not None:
        product.price = price_data.price
    
    db.commit()
    db.refresh(product)
    
    return ProductResponse.model_validate(product)


@products_router.delete("/{product_id}", response_model=MessageResponse)
async def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a product."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    db.delete(product)
    db.commit()
    
    return MessageResponse(message=f"Product '{product.product}' deleted successfully")
