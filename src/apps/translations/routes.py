from typing import List, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from core.database import get_db
from apps.auth.routes import get_current_user  # For protected endpoints
from apps.auth.models import User
from apps.translations.models import Translation
from apps.translations.schemas import (
    TranslationCreate, TranslationResponse, TranslationUpdate,
    BulkTranslationCreate, LanguagePackResponse, CategoryTranslationsResponse,
    TranslationSearchParams, AvailableLanguagesResponse, TranslationStatsResponse
)

translations_router = APIRouter()


# Get language pack for frontend (public endpoint)
@translations_router.get("/language/{language_code}", response_model=LanguagePackResponse)
async def get_language_pack(
    language_code: str,
    category: Optional[str] = Query(None, description="Filter by category"),
    db: Session = Depends(get_db)
):
    """Get all translations for a specific language code."""
    query = db.query(Translation).filter(Translation.language_code == language_code)
    
    if category:
        query = query.filter(Translation.category == category)
    
    translations = query.all()
    
    if not translations:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No translations found for language '{language_code}'"
        )
    
    # Convert to key-value dictionary
    translation_dict = {t.key: t.value for t in translations}
    
    return LanguagePackResponse(
        language_code=language_code,
        translations=translation_dict,
        total_count=len(translation_dict)
    )


# Get translations by category
@translations_router.get("/category/{category}", response_model=List[CategoryTranslationsResponse])
async def get_translations_by_category(
    category: str,
    language_code: Optional[str] = Query(None, description="Filter by language"),
    db: Session = Depends(get_db)
):
    """Get translations for a specific category, optionally filtered by language."""
    query = db.query(Translation).filter(Translation.category == category)
    
    if language_code:
        query = query.filter(Translation.language_code == language_code)
        translations = query.all()
        
        translation_dict = {t.key: t.value for t in translations}
        
        return [CategoryTranslationsResponse(
            language_code=language_code,
            category=category,
            translations=translation_dict,
            count=len(translation_dict)
        )]
    else:
        # Group by language
        translations = query.all()
        grouped = {}
        
        for t in translations:
            if t.language_code not in grouped:
                grouped[t.language_code] = {}
            grouped[t.language_code][t.key] = t.value
        
        return [
            CategoryTranslationsResponse(
                language_code=lang,
                category=category,
                translations=trans_dict,
                count=len(trans_dict)
            )
            for lang, trans_dict in grouped.items()
        ]


# Get available languages
@translations_router.get("/languages", response_model=AvailableLanguagesResponse)
async def get_available_languages(db: Session = Depends(get_db)):
    """Get list of available languages with their codes and names."""
    # Get distinct language codes
    language_codes = db.query(Translation.language_code).distinct().all()
    
    # Map language codes to human-readable names
    language_names = {
        "en": "English",
        "sv": "Svenska",
        "de": "Deutsch",
        "fr": "Français",
        "es": "Español",
        "no": "Norsk",
        "da": "Dansk",
        "fi": "Suomi"
    }
    
    languages = [
        {
            "code": lang[0],
            "name": language_names.get(lang[0], lang[0].upper())
        }
        for lang in language_codes
    ]
    
    return AvailableLanguagesResponse(languages=languages)


# Search translations
@translations_router.get("/search", response_model=List[TranslationResponse])
async def search_translations(
    key: Optional[str] = Query(None, description="Search by key"),
    language_code: Optional[str] = Query(None, description="Filter by language"),
    category: Optional[str] = Query(None, description="Filter by category"),
    search_term: Optional[str] = Query(None, description="Search in values"),
    limit: int = Query(100, le=1000),
    db: Session = Depends(get_db)
):
    """Search translations with various filters."""
    query = db.query(Translation)
    
    # Apply filters
    if key:
        query = query.filter(Translation.key.ilike(f"%{key}%"))
    
    if language_code:
        query = query.filter(Translation.language_code == language_code)
    
    if category:
        query = query.filter(Translation.category == category)
    
    if search_term:
        query = query.filter(or_(
            Translation.key.ilike(f"%{search_term}%"),
            Translation.value.ilike(f"%{search_term}%")
        ))
    
    translations = query.limit(limit).all()
    return [TranslationResponse.model_validate(t) for t in translations]


# Get translation statistics
@translations_router.get("/stats", response_model=TranslationStatsResponse)
async def get_translation_stats(db: Session = Depends(get_db)):
    """Get translation statistics and missing translations."""
    # Total unique keys
    total_keys = db.query(func.count(func.distinct(Translation.key))).scalar()
    
    # Count by language
    lang_counts = db.query(
        Translation.language_code,
        func.count(Translation.id)
    ).group_by(Translation.language_code).all()
    
    languages = {lang: count for lang, count in lang_counts}
    
    # Count by category
    category_counts = db.query(
        Translation.category,
        func.count(Translation.id)
    ).group_by(Translation.category).all()
    
    categories = {cat or "uncategorized": count for cat, count in category_counts}
    
    # Find missing translations (keys that don't exist in all languages)
    all_keys = db.query(func.distinct(Translation.key)).all()
    all_languages = list(languages.keys())
    missing_translations = []
    
    for key_tuple in all_keys:
        key = key_tuple[0]
        existing_langs = db.query(Translation.language_code).filter(
            Translation.key == key
        ).all()
        existing_lang_codes = [lang[0] for lang in existing_langs]
        
        for lang in all_languages:
            if lang not in existing_lang_codes:
                missing_translations.append({
                    "key": key,
                    "missing_language": lang
                })
    
    return TranslationStatsResponse(
        total_keys=total_keys,
        languages=languages,
        categories=categories,
        missing_translations=missing_translations
    )


# Protected endpoints (require authentication)

# Create translation
@translations_router.post("/", response_model=TranslationResponse)
async def create_translation(
    translation: TranslationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new translation (requires authentication)."""
    # Check if translation already exists
    existing = db.query(Translation).filter(
        and_(
            Translation.key == translation.key,
            Translation.language_code == translation.language_code
        )
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Translation for key '{translation.key}' in language '{translation.language_code}' already exists"
        )
    
    db_translation = Translation(**translation.dict())
    db.add(db_translation)
    db.commit()
    db.refresh(db_translation)
    
    return TranslationResponse.model_validate(db_translation)


# Bulk create translations
@translations_router.post("/bulk", response_model=Dict[str, int])
async def create_translations_bulk(
    bulk_data: BulkTranslationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create multiple translations at once (requires authentication)."""
    created_count = 0
    skipped_count = 0
    
    for translation_data in bulk_data.translations:
        # Check if translation already exists
        existing = db.query(Translation).filter(
            and_(
                Translation.key == translation_data.key,
                Translation.language_code == translation_data.language_code
            )
        ).first()
        
        if not existing:
            db_translation = Translation(**translation_data.dict())
            db.add(db_translation)
            created_count += 1
        else:
            skipped_count += 1
    
    db.commit()
    
    return {
        "created": created_count,
        "skipped": skipped_count,
        "total": len(bulk_data.translations)
    }


# Update translation
@translations_router.put("/{translation_id}", response_model=TranslationResponse)
async def update_translation(
    translation_id: int,
    translation_update: TranslationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a translation (requires authentication)."""
    db_translation = db.query(Translation).filter(Translation.id == translation_id).first()
    
    if not db_translation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Translation not found"
        )
    
    # Update fields
    update_data = translation_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_translation, field, value)
    
    db.commit()
    db.refresh(db_translation)
    
    return TranslationResponse.model_validate(db_translation)


# Delete translation
@translations_router.delete("/{translation_id}")
async def delete_translation(
    translation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a translation (requires authentication)."""
    db_translation = db.query(Translation).filter(Translation.id == translation_id).first()
    
    if not db_translation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Translation not found"
        )
    
    db.delete(db_translation)
    db.commit()
    
    return {"message": "Translation deleted successfully"}


# Get single translation
@translations_router.get("/{translation_id}", response_model=TranslationResponse)
async def get_translation(
    translation_id: int,
    db: Session = Depends(get_db)
):
    """Get a single translation by ID."""
    translation = db.query(Translation).filter(Translation.id == translation_id).first()
    
    if not translation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Translation not found"
        )
    
    return TranslationResponse.model_validate(translation)
