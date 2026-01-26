from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct, or_
from typing import List, Optional
import json
from datetime import datetime
from pathlib import Path
from database import get_db
from models import Property
from pydantic import BaseModel

router = APIRouter()

class AutocompleteSuggestion(BaseModel):
    type: str  # 'address', 'town', 'state', 'owner', or 'owner_address'
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
    # Use first property's centroid instead of averaging all (more accurate for specific addresses)
    # This prevents incorrect centers when multiple properties with same address exist in different locations
    address_subquery = db.query(
        Property.address,
        Property.municipality,
        func.min(Property.id).label('first_property_id'),
        func.count(Property.id).label('count')
    ).filter(
        Property.address.ilike(search_term),
        Property.address.isnot(None),
        Property.address != ''
    ).group_by(
        Property.address,
        Property.municipality
    ).having(
        func.count(Property.id) > 0
    ).subquery()
    
    address_results = db.query(
        address_subquery.c.address,
        address_subquery.c.municipality,
        address_subquery.c.count,
        func.ST_Y(func.ST_Centroid(Property.geometry)).label('center_lat'),
        func.ST_X(func.ST_Centroid(Property.geometry)).label('center_lng')
    ).join(
        Property, Property.id == address_subquery.c.first_property_id
    ).order_by(
        address_subquery.c.count.desc()
    ).limit(limit).all()
    
    for result in address_results:
        # Log for debugging Bridgeport vs Torrington
        log_data = {
            "location": "autocomplete.py:55",
            "message": "Address autocomplete result",
            "data": {
                "query": q,
                "address": result.address,
                "municipality": result.municipality,
                "count": result.count,
                "center_lat": float(result.center_lat) if result.center_lat else None,
                "center_lng": float(result.center_lng) if result.center_lng else None,
            },
            "timestamp": int(datetime.now().timestamp() * 1000),
            "sessionId": "debug-session",
            "runId": "run1",
            "hypothesisId": "F"
        }
        try:
            log_file = Path("/Users/jacobmermelstein/Desktop/CT Maps/.cursor/debug.log")
            with open(log_file, "a") as f:
                f.write(json.dumps(log_data) + "\n")
        except:
            pass  # Don't fail if logging fails
        
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
    
    # Get matching owner names
    owner_name_results = db.query(
        Property.owner_name,
        func.count(Property.id).label('count'),
        func.ST_Y(func.ST_Centroid(func.ST_Collect(Property.geometry))).label('center_lat'),
        func.ST_X(func.ST_Centroid(func.ST_Collect(Property.geometry))).label('center_lng')
    ).filter(
        Property.owner_name.ilike(search_term),
        Property.owner_name.isnot(None),
        Property.owner_name != ''
    ).group_by(
        Property.owner_name
    ).having(
        func.count(Property.id) > 0
    ).order_by(
        func.count(Property.id).desc()
    ).limit(5).all()
    
    for result in owner_name_results:
        suggestions.append(AutocompleteSuggestion(
            type='owner',
            value=result.owner_name,
            display=f"{result.owner_name} ({result.count} properties)",
            count=result.count,
            center_lat=float(result.center_lat) if result.center_lat else None,
            center_lng=float(result.center_lng) if result.center_lng else None
        ))
    
    # Get matching owner mailing addresses
    owner_address_results = db.query(
        Property.owner_address,
        Property.owner_city,
        Property.owner_state,
        func.count(Property.id).label('count'),
        func.ST_Y(func.ST_Centroid(func.ST_Collect(Property.geometry))).label('center_lat'),
        func.ST_X(func.ST_Centroid(func.ST_Collect(Property.geometry))).label('center_lng')
    ).filter(
        or_(
            Property.owner_address.ilike(search_term),
            func.concat(
                func.coalesce(Property.owner_address, ''),
                ', ',
                func.coalesce(Property.owner_city, ''),
                ', ',
                func.coalesce(Property.owner_state, '')
            ).ilike(search_term)
        ),
        Property.owner_address.isnot(None),
        Property.owner_address != ''
    ).group_by(
        Property.owner_address,
        Property.owner_city,
        Property.owner_state
    ).having(
        func.count(Property.id) > 0
    ).order_by(
        func.count(Property.id).desc()
    ).limit(5).all()
    
    for result in owner_address_results:
        # Build full address string
        address_parts = [result.owner_address]
        if result.owner_city:
            address_parts.append(result.owner_city)
        if result.owner_state:
            address_parts.append(result.owner_state)
        full_address = ', '.join(address_parts)
        
        suggestions.append(AutocompleteSuggestion(
            type='owner_address',
            value=full_address,
            display=f"{full_address} ({result.count} properties)",
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

@router.get("/owner-cities", response_model=List[str])
async def get_owner_cities(
    municipality: Optional[str] = Query(None, description="Filter by property municipality"),
    unit_type: Optional[str] = Query(None, description="Filter by unit type"),
    zoning: Optional[str] = Query(None, description="Filter by zoning code"),
    property_age: Optional[str] = Query(None, description="Filter by property age range"),
    time_since_sale: Optional[str] = Query(None, description="Filter by time since sale"),
    annual_tax: Optional[str] = Query(None, description="Filter by annual tax range"),
    owner_state: Optional[str] = Query(None, description="Filter by owner mailing state"),
    db: Session = Depends(get_db)
):
    """Get list of all unique owner mailing cities, optionally filtered by other selections"""
    from api.routes.search import apply_filters_to_query
    
    # Build query on full Property table to allow filtering
    query = db.query(Property).filter(
        Property.owner_city.isnot(None),
        Property.owner_city != ''
    )
    
    # Map property_age to year_built_min/max
    year_built_min = None
    year_built_max = None
    if property_age:
        property_age_map = {
            'Built 2020+': (2020, None),
            'Built 2010-2019': (2010, 2019),
            'Built 2000-2009': (2000, 2009),
            'Built 1990-1999': (1990, 1999),
            'Built 1980-1989': (1980, 1989),
            'Built 1970-1979': (1970, 1979),
            'Built 1960-1969': (1960, 1969),
            'Built 1950-1959': (1950, 1959),
            'Built 1940-1949': (1940, 1949),
            'Built 1930-1939': (1930, 1939),
            'Built 1920-1929': (1920, 1929),
            'Built 1900-1919': (1900, 1919),
            'Built Before 1900': (None, 1899),
            'Unknown': (None, None)
        }
        if property_age in property_age_map:
            year_built_min, year_built_max = property_age_map[property_age]
    
    # Apply all filters
    query = apply_filters_to_query(
        query,
        municipality=municipality,
        unit_type=unit_type,
        zoning=zoning,
        year_built_min=year_built_min,
        year_built_max=year_built_max,
        time_since_sale=time_since_sale,
        annual_tax=annual_tax,
        owner_state=owner_state
    )
    
    # Get unique owner cities
    properties = query.all()
    cities = set()
    for prop in properties:
        if prop.owner_city:
            cities.add(prop.owner_city)
    
    return sorted(list(cities))

@router.get("/owner-states", response_model=List[str])
async def get_owner_states(
    municipality: Optional[str] = Query(None, description="Filter by property municipality"),
    unit_type: Optional[str] = Query(None, description="Filter by unit type"),
    zoning: Optional[str] = Query(None, description="Filter by zoning code"),
    property_age: Optional[str] = Query(None, description="Filter by property age range"),
    time_since_sale: Optional[str] = Query(None, description="Filter by time since sale"),
    annual_tax: Optional[str] = Query(None, description="Filter by annual tax range"),
    owner_city: Optional[str] = Query(None, description="Filter by owner mailing city"),
    db: Session = Depends(get_db)
):
    """Get list of all unique owner mailing states, optionally filtered by other selections"""
    from api.routes.search import apply_filters_to_query
    
    # Build query on full Property table to allow filtering
    query = db.query(Property).filter(
        Property.owner_state.isnot(None),
        Property.owner_state != ''
    )
    
    # Map property_age to year_built_min/max
    year_built_min = None
    year_built_max = None
    if property_age:
        property_age_map = {
            'Built 2020+': (2020, None),
            'Built 2010-2019': (2010, 2019),
            'Built 2000-2009': (2000, 2009),
            'Built 1990-1999': (1990, 1999),
            'Built 1980-1989': (1980, 1989),
            'Built 1970-1979': (1970, 1979),
            'Built 1960-1969': (1960, 1969),
            'Built 1950-1959': (1950, 1959),
            'Built 1940-1949': (1940, 1949),
            'Built 1930-1939': (1930, 1939),
            'Built 1920-1929': (1920, 1929),
            'Built 1900-1919': (1900, 1919),
            'Built Before 1900': (None, 1899),
            'Unknown': (None, None)
        }
        if property_age in property_age_map:
            year_built_min, year_built_max = property_age_map[property_age]
    
    # Apply all filters
    query = apply_filters_to_query(
        query,
        municipality=municipality,
        unit_type=unit_type,
        zoning=zoning,
        year_built_min=year_built_min,
        year_built_max=year_built_max,
        time_since_sale=time_since_sale,
        annual_tax=annual_tax,
        owner_city=owner_city
    )
    
    # Get unique owner states
    properties = query.all()
    states = set()
    for prop in properties:
        if prop.owner_state:
            states.add(prop.owner_state)
    
    return sorted(list(states))

@router.get("/owner-addresses", response_model=List[str])
async def get_owner_addresses(
    q: str = Query(..., min_length=1, description="Search query for owner address"),
    municipality: Optional[str] = Query(None, description="Filter by property municipality"),
    unit_type: Optional[str] = Query(None, description="Filter by unit type"),
    zoning: Optional[str] = Query(None, description="Filter by zoning code"),
    property_age: Optional[str] = Query(None, description="Filter by property age range"),
    time_since_sale: Optional[str] = Query(None, description="Filter by time since sale"),
    annual_tax: Optional[str] = Query(None, description="Filter by annual tax range"),
    owner_city: Optional[str] = Query(None, description="Filter by owner mailing city"),
    owner_state: Optional[str] = Query(None, description="Filter by owner mailing state"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of suggestions"),
    db: Session = Depends(get_db)
):
    """Get autocomplete suggestions for owner mailing addresses, optionally filtered by other selections"""
    from api.routes.search import apply_filters_to_query
    
    search_term = f"%{q}%"
    
    # Build query on full Property table to allow filtering
    query = db.query(Property).filter(
        Property.owner_address.isnot(None),
        Property.owner_address != '',
        Property.owner_address.ilike(search_term)
    )
    
    # Map property_age to year_built_min/max
    year_built_min = None
    year_built_max = None
    if property_age:
        property_age_map = {
            'Built 2020+': (2020, None),
            'Built 2010-2019': (2010, 2019),
            'Built 2000-2009': (2000, 2009),
            'Built 1990-1999': (1990, 1999),
            'Built 1980-1989': (1980, 1989),
            'Built 1970-1979': (1970, 1979),
            'Built 1960-1969': (1960, 1969),
            'Built 1950-1959': (1950, 1959),
            'Built 1940-1949': (1940, 1949),
            'Built 1930-1939': (1930, 1939),
            'Built 1920-1929': (1920, 1929),
            'Built 1900-1919': (1900, 1919),
            'Built Before 1900': (None, 1899),
            'Unknown': (None, None)
        }
        if property_age in property_age_map:
            year_built_min, year_built_max = property_age_map[property_age]
    
    # Apply all filters
    query = apply_filters_to_query(
        query,
        municipality=municipality,
        unit_type=unit_type,
        zoning=zoning,
        year_built_min=year_built_min,
        year_built_max=year_built_max,
        time_since_sale=time_since_sale,
        annual_tax=annual_tax,
        owner_city=owner_city,
        owner_state=owner_state
    )
    
    # Get unique owner addresses from filtered results
    properties = query.all()
    addresses = set()
    for prop in properties:
        if prop.owner_address:
            addresses.add(prop.owner_address)
    
    # Sort and limit
    sorted_addresses = sorted(list(addresses))
    return sorted_addresses[:limit]
