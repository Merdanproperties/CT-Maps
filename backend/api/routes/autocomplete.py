from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct, or_
from typing import List, Optional
from database import get_db
from models import Property
from pydantic import BaseModel

router = APIRouter()

class AutocompleteSuggestion(BaseModel):
    type: str  # 'address', 'town', or 'state'
    value: str
    display: str
    count: Optional[int] = None
    center_lat: Optional[float] = None
    center_lng: Optional[float] = None

class AutocompleteResponse(BaseModel):
    suggestions: List[AutocompleteSuggestion]

@router.get("/", response_model=AutocompleteResponse)
async def autocomplete(
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of suggestions"),
    db: Session = Depends(get_db)
):
    """
    Autocomplete suggestions for addresses and towns.
    Returns matching addresses and towns based on the search query.
    """
    suggestions: List[AutocompleteSuggestion] = []
    search_term = f"%{q}%"
    
    # Get matching addresses
    address_results = db.query(
        Property.address,
        Property.municipality,
        func.count(Property.id).label('count'),
        func.ST_Y(func.ST_Centroid(func.ST_Collect(Property.geometry))).label('center_lat'),
        func.ST_X(func.ST_Centroid(func.ST_Collect(Property.geometry))).label('center_lng')
    ).filter(
        Property.address.ilike(search_term),
        Property.address.isnot(None),
        Property.address != ''
    ).group_by(
        Property.address,
        Property.municipality
    ).having(
        func.count(Property.id) > 0
    ).order_by(
        func.count(Property.id).desc()
    ).limit(limit).all()
    
    for result in address_results:
        suggestions.append(AutocompleteSuggestion(
            type='address',
            value=result.address,
            display=f"{result.address}, {result.municipality or 'CT'}" if result.municipality else result.address,
            count=result.count,
            center_lat=float(result.center_lat) if result.center_lat else None,
            center_lng=float(result.center_lng) if result.center_lng else None
        ))
    
    # Get matching towns/municipalities
    town_results = db.query(
        Property.municipality,
        func.count(Property.id).label('count'),
        func.ST_Y(func.ST_Centroid(func.ST_Collect(Property.geometry))).label('center_lat'),
        func.ST_X(func.ST_Centroid(func.ST_Collect(Property.geometry))).label('center_lng')
    ).filter(
        Property.municipality.ilike(search_term),
        Property.municipality.isnot(None),
        Property.municipality != ''
    ).group_by(
        Property.municipality
    ).order_by(
        func.count(Property.id).desc()
    ).limit(limit).all()
    
    for result in town_results:
        suggestions.append(AutocompleteSuggestion(
            type='town',
            value=result.municipality,
            display=f"{result.municipality}, CT ({result.count:,} properties)",
            count=result.count,
            center_lat=float(result.center_lat) if result.center_lat else None,
            center_lng=float(result.center_lng) if result.center_lng else None
        ))
    
    # Add state suggestions (CT, Connecticut)
    state_query = q.upper().strip()
    if state_query in ['CT', 'CONN', 'CONNECTICUT'] or 'connecticut' in q.lower():
        # Get total count of all properties in CT
        total_count = db.query(func.count(Property.id)).scalar() or 0
        if total_count > 0:
            # CT center coordinates (approximate)
            suggestions.append(AutocompleteSuggestion(
                type='state',
                value='CT',
                display=f'Connecticut ({total_count:,} properties)',
                count=total_count,
                center_lat=41.6,
                center_lng=-72.7
            ))
    
    # Sort by relevance (exact matches first, then by count)
    def sort_key(s: AutocompleteSuggestion):
        exact_match = s.value.lower().startswith(q.lower()) or s.display.lower().startswith(q.lower())
        return (not exact_match, -s.count if s.count else 0)
    
    suggestions.sort(key=sort_key)
    
    return AutocompleteResponse(suggestions=suggestions[:limit])

@router.get("/towns", response_model=List[str])
async def get_towns(
    db: Session = Depends(get_db)
):
    """Get list of all unique towns/municipalities"""
    towns = db.query(distinct(Property.municipality)).filter(
        Property.municipality.isnot(None),
        Property.municipality != ''
    ).order_by(Property.municipality).all()
    
    return [town[0] for town in towns if town[0]]
