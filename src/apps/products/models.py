from sqlalchemy import Column, Integer, String, Float, Text, DateTime
from sqlalchemy.sql import func
from core.database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    article_number = Column(String, unique=True, index=True, nullable=False)
    product = Column(String, nullable=False)  # Product name
    in_price = Column(Float, nullable=False)  # Purchase/cost price
    price = Column(Float, nullable=False)     # Selling price
    unit = Column(String, nullable=False)     # Unit of measurement (kg, pieces, liters, etc.)
    stock = Column(Integer, default=0)        # Stock quantity
    description = Column(Text, nullable=True) # Product description
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<Product(article_number='{self.article_number}', product='{self.product}', stock={self.stock})>"