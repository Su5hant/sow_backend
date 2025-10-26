from sqlalchemy import Column, Integer, String, Text, DateTime, Index
from sqlalchemy.sql import func
from core.database import Base


class Translation(Base):
    __tablename__ = "translations"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(255), nullable=False, index=True)  # e.g., "nav.home", "auth.login"
    language_code = Column(String(10), nullable=False, index=True)  # "en", "sv"
    value = Column(Text, nullable=False)  # The translated text
    category = Column(String(100), nullable=True, index=True)  # "navigation", "auth", "general"
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Create composite index for faster lookups
    __table_args__ = (
        Index('idx_key_language', 'key', 'language_code'),
        Index('idx_category_language', 'category', 'language_code'),
    )

    def __repr__(self):
        return f"<Translation(key='{self.key}', lang='{self.language_code}', value='{self.value[:50]}...')>"