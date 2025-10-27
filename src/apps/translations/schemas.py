from typing import Optional, Dict, List
from pydantic import BaseModel
from datetime import datetime


# Base Translation schema
class TranslationBase(BaseModel):
    key: str
    language_code: str
    value: str
    category: Optional[str] = None


# Translation creation schema
class TranslationCreate(TranslationBase):
    pass


# Translation update schema
class TranslationUpdate(BaseModel):
    value: Optional[str] = None
    category: Optional[str] = None


# Translation response schema
class TranslationResponse(TranslationBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Bulk translation create schema
class BulkTranslationCreate(BaseModel):
    translations: List[TranslationCreate]


# Language pack response schema (for frontend consumption)
class LanguagePackResponse(BaseModel):
    language_code: str
    translations: Dict[str, str]  # key-value pairs
    total_count: int


# Category-based translation response
class CategoryTranslationsResponse(BaseModel):
    language_code: str
    category: str
    translations: Dict[str, str]
    count: int


# Translation key search schema
class TranslationSearchParams(BaseModel):
    key: Optional[str] = None
    language_code: Optional[str] = None
    category: Optional[str] = None
    search_term: Optional[str] = None


# Response for available languages
class AvailableLanguagesResponse(BaseModel):
    languages: List[Dict[str, str]]  # [{"code": "en", "name": "English"}, ...]


# Translation statistics response
class TranslationStatsResponse(BaseModel):
    total_keys: int
    languages: Dict[str, int]  # {"en": 45, "sv": 43}
    categories: Dict[str, int]  # {"navigation": 10, "auth": 15}
    missing_translations: List[Dict[str, str]]  # Keys missing in some languages