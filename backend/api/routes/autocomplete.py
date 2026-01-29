from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct, or_, text
from sqlalchemy.exc import OperationalError
from typing import List, Optional
import json
from datetime import datetime
from pathlib import Path
from database import get_db
from models import Property
from pydantic import BaseModel
from services.options_cache import options_cache

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
    search_type: Optional[str] = Query(None, description="Limit to: address, town, owner. Omit for all types (slower)."),
    db: Session = Depends(get_db)
):
    """
    Autocomplete suggestions for addresses, towns, and owners.
    Use search_type=address|town|owner to run only one query (faster). Omit for all.
    """
    suggestions: List[AutocompleteSuggestion] = []
    search_term = f"%{q}%"
    want_address = search_type is None or search_type == "address"
    want_town = search_type is None or search_type == "town"
    want_owner = search_type is None or search_type == "owner"

    # Get matching addresses (only when type is None or address)
    if want_address:
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

    # Get matching towns/municipalities (only when type is None or town)
    if want_town:
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

    # Get matching owner names (only when type is None or owner)
    if want_owner:
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

        # Get matching owner mailing addresses (same request as owner)
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

    # Add state suggestions (CT, Connecticut) only when no search_type filter (full search)
    if search_type is None:
        state_query = q.upper().strip()
        if state_query in ['CT', 'CONN', 'CONNECTICUT'] or 'connecticut' in q.lower():
            total_count = db.query(func.count(Property.id)).scalar() or 0
            if total_count > 0:
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
    """Get list of all unique towns/municipalities. Cached 10 min; 10s timeout; returns [] on timeout."""
    cached = options_cache.get("towns")
    if cached is not None:
        return cached
    try:
        db.execute(text("SET statement_timeout = '10s'"))
        try:
            query = db.query(Property).filter(
                Property.municipality.isnot(None),
                Property.municipality != ''
            ).with_entities(Property.municipality).distinct().order_by(Property.municipality)
            rows = query.all()
            result = [r[0] for r in rows if r[0]]
            options_cache.set("towns", result)
            return result
        except OperationalError as oe:
            err = str(oe).lower()
            if "canceling" in err or "timeout" in err or "statement_timeout" in err:
                return []
            raise
        finally:
            try:
                db.execute(text("SET statement_timeout = '0'"))
            except Exception:
                pass
    except OperationalError as oe:
        err = str(oe).lower()
        if "canceling" in err or "timeout" in err or "statement_timeout" in err:
            return []
        raise

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
    
    cached = options_cache.get(
        "owner-cities",
        municipality=municipality,
        unit_type=unit_type,
        zoning=zoning,
        property_age=property_age,
        time_since_sale=time_since_sale,
        annual_tax=annual_tax,
        owner_state=owner_state,
    )
    if cached is not None:
        return cached
    # 10s statement timeout; return [] on timeout
    try:
        db.execute(text("SET statement_timeout = '10s'"))
        try:
            query = query.with_entities(Property.owner_city).distinct()
            rows = query.all()
            result = sorted([r[0] for r in rows if r[0]])
            options_cache.set(
                "owner-cities",
                result,
                municipality=municipality,
                unit_type=unit_type,
                zoning=zoning,
                property_age=property_age,
                time_since_sale=time_since_sale,
                annual_tax=annual_tax,
                owner_state=owner_state,
            )
            return result
        except OperationalError as oe:
            err = str(oe).lower()
            if "canceling" in err or "timeout" in err or "statement_timeout" in err:
                return []
            raise
        finally:
            try:
                db.execute(text("SET statement_timeout = '0'"))
            except Exception:
                pass
    except OperationalError as oe:
        err = str(oe).lower()
        if "canceling" in err or "timeout" in err or "statement_timeout" in err:
            return []
        raise

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
    
    cached = options_cache.get(
        "owner-states",
        municipality=municipality,
        unit_type=unit_type,
        zoning=zoning,
        property_age=property_age,
        time_since_sale=time_since_sale,
        annual_tax=annual_tax,
        owner_city=owner_city,
    )
    if cached is not None:
        return cached
    # 10s statement timeout; return [] on timeout
    try:
        db.execute(text("SET statement_timeout = '10s'"))
        try:
            query = query.with_entities(Property.owner_state).distinct()
            rows = query.all()
            result = sorted([r[0] for r in rows if r[0]])
            options_cache.set(
                "owner-states",
                result,
                municipality=municipality,
                unit_type=unit_type,
                zoning=zoning,
                property_age=property_age,
                time_since_sale=time_since_sale,
                annual_tax=annual_tax,
                owner_city=owner_city,
            )
            return result
        except OperationalError as oe:
            err = str(oe).lower()
            if "canceling" in err or "timeout" in err or "statement_timeout" in err:
                return []
            raise
        finally:
            try:
                db.execute(text("SET statement_timeout = '0'"))
            except Exception:
                pass
    except OperationalError as oe:
        err = str(oe).lower()
        if "canceling" in err or "timeout" in err or "statement_timeout" in err:
            return []
        raise

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
    
    # SELECT DISTINCT owner_address only (no full row load), then sort and limit
    query = query.with_entities(Property.owner_address).distinct()
    rows = query.all()
    addresses = sorted([r[0] for r in rows if r[0]])
    return addresses[:limit]
