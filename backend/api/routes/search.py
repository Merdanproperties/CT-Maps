from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_, extract, select, text
from typing import Optional, List
from database import get_db
from models import Property
from api.routes.properties import PropertyResponse
from pydantic import BaseModel
from datetime import date, datetime, timedelta
import json

router = APIRouter()

def get_family_count(property_type: str) -> Optional[int]:
    """Detect family count from property_type string"""
    if not property_type:
        return None
    prop_type_lower = property_type.lower()
    if 'two' in prop_type_lower or '2' in prop_type_lower or 'duplex' in prop_type_lower:
        return 2
    if 'three' in prop_type_lower or '3' in prop_type_lower or 'triplex' in prop_type_lower:
        return 3
    if 'four' in prop_type_lower or '4' in prop_type_lower:
        return 4
    if 'five' in prop_type_lower or '5' in prop_type_lower or ('multi' in prop_type_lower and 'family' in prop_type_lower):
        return 5  # 5+
    return None

class SearchResponse(BaseModel):
    properties: List[PropertyResponse]
    total: int
    page: int
    page_size: int

@router.get("/", response_model=SearchResponse)
async def search_properties(
    q: Optional[str] = Query(None, description="Search query (address, owner, parcel ID)"),
    municipality: Optional[str] = None,
    min_value: Optional[float] = None,
    max_value: Optional[float] = None,
    property_type: Optional[str] = None,
    min_lot_size: Optional[float] = Query(None, description="Minimum lot size in square feet"),
    max_lot_size: Optional[float] = Query(None, description="Maximum lot size in square feet"),
    bbox: Optional[str] = Query(None, description="Bounding box: min_lng,min_lat,max_lng,max_lat"),
    # New filter parameters
    unit_type: Optional[str] = Query(None, description="Unit type: formatted string with property_type and land_use (e.g., 'Single Family - Residential'). For multiple values, pass comma-separated string or use unit_type[] parameter multiple times."),
    zoning: Optional[str] = Query(None, description="Zoning code. For multiple values, pass comma-separated string or use zoning[] parameter multiple times."),
    year_built_min: Optional[int] = Query(None, description="Minimum year built"),
    year_built_max: Optional[int] = Query(None, description="Maximum year built"),
    has_phone: Optional[bool] = Query(None, description="Has owner phone"),
    has_email: Optional[bool] = Query(None, description="Has owner email"),
    has_contact: Optional[str] = Query(None, description="Has contact: Has Phone, Has Email, Has Both, Missing Contact Info"),
    sales_history: Optional[str] = Query(None, description="Sales history: Multiple Sales, Single Sale, Never Sold, Sold Recently"),
    days_since_sale_min: Optional[int] = Query(None, description="Minimum days since sale"),
    days_since_sale_max: Optional[int] = Query(None, description="Maximum days since sale"),
    time_since_sale: Optional[str] = Query(None, description="Time since sale: Last 2 Years, 2-5 Years Ago, 5-10 Years Ago, 10-20 Years Ago, 20+ Years Ago, Never Sold"),
    tax_amount_min: Optional[float] = Query(None, description="Minimum annual tax amount"),
    tax_amount_max: Optional[float] = Query(None, description="Maximum annual tax amount"),
    annual_tax: Optional[str] = Query(None, description="Annual tax range: Under $2,000, $2,000 - $5,000, $5,000 - $10,000, $10,000 - $20,000, $20,000+"),
    owner_address: Optional[str] = Query(None, description="Filter by owner mailing address (partial match)"),
    owner_city: Optional[str] = Query(None, description="Filter by owner mailing city. For multiple values, pass comma-separated string."),
    owner_state: Optional[str] = Query(None, description="Filter by owner mailing state. For multiple values, pass comma-separated string."),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=2000),  # Balanced limit: 2k properties ~1.6MB
    db: Session = Depends(get_db)
):
    """Search properties with various filters"""
    try:
        query = db.query(Property)
        
        # Text search
        if q:
            search_term = f"%{q}%"
            # Normalize search query for better matching (handle ST vs Street, etc.)
            # This helps match "12 Margerie st" with "12 MARGERIE ST" or "12 Margerie Street"
            normalized_q = q.upper().strip()
            # Replace common abbreviations with full words for better matching
            normalized_q = normalized_q.replace(' ST ', ' STREET ').replace(' ST,', ' STREET,').replace(' ST', ' STREET')
            normalized_q = normalized_q.replace(' AVE ', ' AVENUE ').replace(' AVE,', ' AVENUE,').replace(' AVE', ' AVENUE')
            normalized_q = normalized_q.replace(' RD ', ' ROAD ').replace(' RD,', ' ROAD,').replace(' RD', ' ROAD')
            normalized_q = normalized_q.replace(' DR ', ' DRIVE ').replace(' DR,', ' DRIVE,').replace(' DR', ' DRIVE')
            normalized_search_term = f"%{normalized_q}%"
            
            # Build concatenated owner address for full address matching
            owner_full_address = func.concat(
                func.coalesce(Property.owner_address, ''),
                ', ',
                func.coalesce(Property.owner_city, ''),
                ', ',
                func.coalesce(Property.owner_state, '')
            )
            query = query.filter(
                or_(
                    Property.address.ilike(search_term),
                    func.upper(Property.address).ilike(normalized_search_term),  # Also try normalized search
                    Property.owner_name.ilike(search_term),
                    Property.owner_address.ilike(search_term),
                    owner_full_address.ilike(search_term),  # Match full owner address string
                    Property.parcel_id.ilike(search_term),
                    Property.city.ilike(search_term),
                    Property.municipality.ilike(search_term)  # Also search municipality
                )
            )
        
        # Municipality filter - supports both single value and comma-separated values
        if municipality:
            # Handle comma-separated values
            municipalities = [m.strip() for m in municipality.split(',')] if isinstance(municipality, str) else [municipality]
            municipalities = [m for m in municipalities if m]  # Filter out empty strings
            
            if municipalities:
                if len(municipalities) == 1:
                    municipality_clean = municipalities[0]
                    query = query.filter(
                        or_(
                            Property.municipality == municipality_clean,
                            Property.municipality.ilike(f"%{municipality_clean}%")
                        )
                    )
                else:
                    # Multiple municipalities: use OR condition
                    municipality_filters = []
                    for m in municipalities:
                        municipality_clean = m.strip()
                        municipality_filters.append(
                            or_(
                                Property.municipality == municipality_clean,
                                Property.municipality.ilike(f"%{municipality_clean}%")
                            )
                        )
                    query = query.filter(or_(*municipality_filters))
        
        # Value range filter
        if min_value is not None:
            query = query.filter(Property.assessed_value >= min_value)
        if max_value is not None:
            query = query.filter(Property.assessed_value <= max_value)
        
        # Property type filter (case-insensitive partial match for flexibility)
        if property_type:
            query = query.filter(Property.property_type.ilike(f"%{property_type}%"))
        
        # Unit type filter (matches on both property_type and land_use)
        # Supports both single value and comma-separated values
        if unit_type:
            # Handle comma-separated values
            unit_types = [ut.strip() for ut in unit_type.split(',')] if isinstance(unit_type, str) else [unit_type]
            unit_type_filters = []
            
            for ut in unit_types:
                if not ut:
                    continue
                # Parse the formatted string (e.g., "Single Family - Residential" or just "Single Family")
                # Split by " - " to get property_type and land_use
                parts = ut.split(" - ", 1)
                parsed_property_type = parts[0].strip() if parts else None
                parsed_land_use = parts[1].strip() if len(parts) > 1 and parts[1] else None
                
                # Build filter conditions for this unit type
                filters = []
                
                if parsed_property_type:
                    filters.append(Property.property_type.ilike(f"%{parsed_property_type}%"))
                
                if parsed_land_use:
                    filters.append(Property.land_use.ilike(f"%{parsed_land_use}%"))
                
                # Both must match if both are present
                if len(filters) == 2:
                    unit_type_filters.append(and_(*filters))
                elif len(filters) == 1:
                    unit_type_filters.append(filters[0])
            
            # Apply OR condition for multiple unit types
            if unit_type_filters:
                if len(unit_type_filters) == 1:
                    query = query.filter(unit_type_filters[0])
                else:
                    query = query.filter(or_(*unit_type_filters))
        
        # Zoning filter - supports both single value and comma-separated values
        if zoning:
            # Handle comma-separated values
            zoning_codes = [zc.strip() for zc in zoning.split(',')] if isinstance(zoning, str) else [zoning]
            zoning_codes = [zc for zc in zoning_codes if zc]  # Filter out empty strings
            if zoning_codes:
                if len(zoning_codes) == 1:
                    query = query.filter(Property.zoning.ilike(f"%{zoning_codes[0]}%"))
                else:
                    zoning_filters = [Property.zoning.ilike(f"%{zc}%") for zc in zoning_codes]
                    query = query.filter(or_(*zoning_filters))
        
        # Property age filter (year built)
        if year_built_min is not None:
            query = query.filter(Property.year_built >= year_built_min)
        if year_built_max is not None:
            query = query.filter(Property.year_built <= year_built_max)
        
        # Contact info filters
        if has_phone is not None:
            if has_phone:
                query = query.filter(
                    Property.owner_phone.isnot(None),
                    Property.owner_phone != ''
                )
            else:
                query = query.filter(
                    or_(
                        Property.owner_phone.is_(None),
                        Property.owner_phone == ''
                    )
                )
        
        if has_email is not None:
            if has_email:
                query = query.filter(
                    Property.owner_email.isnot(None),
                    Property.owner_email != ''
                )
            else:
                query = query.filter(
                    or_(
                        Property.owner_email.is_(None),
                        Property.owner_email == ''
                    )
                )
        
        if has_contact:
            if has_contact == "Has Phone":
                query = query.filter(
                    Property.owner_phone.isnot(None),
                    Property.owner_phone != ''
                )
            elif has_contact == "Has Email":
                query = query.filter(
                    Property.owner_email.isnot(None),
                    Property.owner_email != ''
                )
            elif has_contact == "Has Both":
                query = query.filter(
                    Property.owner_phone.isnot(None),
                    Property.owner_phone != '',
                    Property.owner_email.isnot(None),
                    Property.owner_email != ''
                )
            elif has_contact == "Missing Contact Info":
                query = query.filter(
                    or_(
                        and_(
                            or_(Property.owner_phone.is_(None), Property.owner_phone == ''),
                            or_(Property.owner_email.is_(None), Property.owner_email == '')
                        )
                    )
                )
        
        # Sales history filter
        if sales_history:
            if sales_history == "Multiple Sales":
                query = query.filter(Property.sales_count >= 2)
            elif sales_history == "Single Sale":
                query = query.filter(Property.sales_count == 1)
            elif sales_history == "Never Sold":
                query = query.filter(
                    or_(
                        Property.sales_count == 0,
                        Property.sales_count.is_(None),
                        Property.last_sale_date.is_(None)
                    )
                )
            elif sales_history == "Sold Recently":
                two_years_ago = date.today() - timedelta(days=730)
                query = query.filter(
                    Property.last_sale_date >= two_years_ago
                )
        
        # Time since sale filter
        if time_since_sale:
            today = date.today()
            if time_since_sale == "Last 2 Years":
                two_years_ago = today - timedelta(days=730)
                query = query.filter(Property.last_sale_date >= two_years_ago)
            elif time_since_sale == "2-5 Years Ago":
                two_years_ago = today - timedelta(days=730)
                five_years_ago = today - timedelta(days=1825)
                query = query.filter(
                    and_(
                        Property.last_sale_date < two_years_ago,
                        Property.last_sale_date >= five_years_ago
                    )
                )
            elif time_since_sale == "5-10 Years Ago":
                five_years_ago = today - timedelta(days=1825)
                ten_years_ago = today - timedelta(days=3650)
                query = query.filter(
                    and_(
                        Property.last_sale_date < five_years_ago,
                        Property.last_sale_date >= ten_years_ago
                    )
                )
            elif time_since_sale == "10-20 Years Ago":
                ten_years_ago = today - timedelta(days=3650)
                twenty_years_ago = today - timedelta(days=7300)
                query = query.filter(
                    and_(
                        Property.last_sale_date < ten_years_ago,
                        Property.last_sale_date >= twenty_years_ago
                    )
                )
            elif time_since_sale == "20+ Years Ago":
                twenty_years_ago = today - timedelta(days=7300)
                query = query.filter(Property.last_sale_date < twenty_years_ago)
            elif time_since_sale == "Never Sold":
                query = query.filter(Property.last_sale_date.is_(None))
        
        # Days since sale filter (alternative to time_since_sale)
        if days_since_sale_min is not None:
            query = query.filter(Property.days_since_sale >= days_since_sale_min)
        if days_since_sale_max is not None:
            query = query.filter(Property.days_since_sale <= days_since_sale_max)
        
        # Tax amount filter
        if tax_amount_min is not None:
            query = query.filter(Property.tax_amount >= tax_amount_min)
        if tax_amount_max is not None:
            query = query.filter(Property.tax_amount <= tax_amount_max)
        
        # Annual tax range filter
        if annual_tax:
            if annual_tax == "Under $2,000":
                query = query.filter(
                    or_(
                        Property.tax_amount < 2000,
                        Property.tax_amount.is_(None)
                    )
                )
            elif annual_tax == "$2,000 - $5,000":
                query = query.filter(
                    and_(
                        Property.tax_amount >= 2000,
                        Property.tax_amount < 5000
                    )
                )
            elif annual_tax == "$5,000 - $10,000":
                query = query.filter(
                    and_(
                        Property.tax_amount >= 5000,
                        Property.tax_amount < 10000
                    )
                )
            elif annual_tax == "$10,000 - $20,000":
                query = query.filter(
                    and_(
                        Property.tax_amount >= 10000,
                        Property.tax_amount < 20000
                    )
                )
            elif annual_tax == "$20,000+":
                query = query.filter(Property.tax_amount >= 20000)
        
        # Owner mailing address filter
        if owner_address:
            query = query.filter(Property.owner_address.ilike(f"%{owner_address}%"))
        
        # Owner city filter - supports both single value and comma-separated values
        if owner_city:
            owner_cities = [c.strip() for c in owner_city.split(',')] if isinstance(owner_city, str) else [owner_city]
            owner_cities = [c for c in owner_cities if c]
            if owner_cities:
                if len(owner_cities) == 1:
                    query = query.filter(Property.owner_city.ilike(f"%{owner_cities[0]}%"))
                else:
                    owner_city_filters = [Property.owner_city.ilike(f"%{c}%") for c in owner_cities]
                    query = query.filter(or_(*owner_city_filters))
        
        # Owner state filter - supports both single value and comma-separated values
        if owner_state:
            owner_states = [s.strip().upper() for s in owner_state.split(',')] if isinstance(owner_state, str) else [owner_state.upper()]
            owner_states = [s for s in owner_states if s]
            if owner_states:
                if len(owner_states) == 1:
                    query = query.filter(
                        or_(
                            Property.owner_state == owner_states[0],
                            Property.owner_state.ilike(f"%{owner_states[0]}%")
                        )
                    )
                else:
                    owner_state_filters = []
                    for s in owner_states:
                        owner_state_filters.append(
                            or_(
                                Property.owner_state == s,
                                Property.owner_state.ilike(f"%{s}%")
                            )
                        )
                    query = query.filter(or_(*owner_state_filters))
        
        # Lot size filter
        if min_lot_size is not None:
            query = query.filter(Property.lot_size_sqft >= min_lot_size)
        if max_lot_size is not None:
            query = query.filter(Property.lot_size_sqft <= max_lot_size)
        
        # Bounding box filter (spatial)
        if bbox:
            try:
                coords = [float(x) for x in bbox.split(",")]
                if len(coords) == 4:
                    min_lng, min_lat, max_lng, max_lat = coords
                    bbox_geom = func.ST_MakeEnvelope(min_lng, min_lat, max_lng, max_lat, 4326)
                    query = query.filter(
                        func.ST_Intersects(Property.geometry, bbox_geom)
                    )
            except ValueError:
                pass
        
        # Get total count
        total = query.count()
        
        # Pagination
        skip = (page - 1) * page_size
        properties = query.offset(skip).limit(page_size).all()
        
        # Convert to response format
        results = []
        for prop in properties:
            try:
                # Get geometry as GeoJSON - handle null geometries
                # Use text() with parameterized query for reliable geometry conversion
                geom_result = None
                if prop.geometry is not None:
                    try:
                        geom_result = db.execute(
                            text("SELECT ST_AsGeoJSON(geometry) FROM properties WHERE id = :id"),
                            {"id": prop.id}
                        ).scalar()
                    except Exception as geom_error:
                        import traceback
                        error_details = f"Error converting geometry for property {prop.id}: {str(geom_error)}"
                        print(error_details)
                        traceback.print_exc()
                        geom_result = None
                
                # Parse geometry JSON if available
                geometry_data = None
                if geom_result:
                    try:
                        geometry_data = json.loads(geom_result)
                    except json.JSONDecodeError as json_error:
                        print(f"Error parsing GeoJSON for property {prop.id}: {str(json_error)}")
                        geometry_data = None
                
                # Create response object manually to avoid from_orm issues
                result = PropertyResponse(
                    id=prop.id,
                    parcel_id=prop.parcel_id,
                    address=prop.address,
                    city=prop.city,
                    municipality=prop.municipality,
                    zip_code=prop.zip_code,
                    owner_name=prop.owner_name,
                    owner_phone=prop.owner_phone,
                    owner_email=prop.owner_email,
                    assessed_value=prop.assessed_value,
                    land_value=prop.land_value,
                    building_value=prop.building_value,
                    property_type=prop.property_type,
                    land_use=prop.land_use,
                    zoning=prop.zoning,
                    lot_size_sqft=prop.lot_size_sqft,
                    year_built=prop.year_built,
                    last_sale_date=prop.last_sale_date,
                    last_sale_price=prop.last_sale_price,
                    is_absentee=prop.is_absentee or 0,
                    is_vacant=prop.is_vacant or 0,
                    equity_estimate=prop.equity_estimate,
                    geometry={"type": "Feature", "geometry": geometry_data}
                )
                results.append(result)
            except Exception as e:
                # Skip properties with errors but log them
                import traceback
                error_details = f"Error processing property {prop.id if prop else 'unknown'}: {str(e)}"
                print(error_details)
                traceback.print_exc()
                continue
        
        return SearchResponse(
            properties=results,
            total=total,
            page=page,
            page_size=page_size
        )
    except Exception as e:
        import traceback
        error_msg = f"Error in search_properties: {str(e)}"
        print(error_msg)
        traceback.print_exc()
        from fastapi import HTTPException
        # Include more context in error message for debugging
        raise HTTPException(
            status_code=500, 
            detail=f"Search failed: {str(e)}. Check backend logs for full traceback."
        )

class ZoningOptionsResponse(BaseModel):
    zoning_codes: List[str]

class UnitTypeOption(BaseModel):
    property_type: str
    land_use: Optional[str]

class UnitTypeOptionsResponse(BaseModel):
    unit_types: List[UnitTypeOption]

def apply_filters_to_query(
    query,
    municipality: Optional[str] = None,
    unit_type: Optional[str] = None,
    zoning: Optional[str] = None,
    year_built_min: Optional[int] = None,
    year_built_max: Optional[int] = None,
    time_since_sale: Optional[str] = None,
    annual_tax: Optional[str] = None,
    owner_address: Optional[str] = None,
    owner_city: Optional[str] = None,
    owner_state: Optional[str] = None
):
    """Helper function to apply all filters to a query"""
    # Municipality filter
    if municipality:
        municipalities = [m.strip() for m in municipality.split(',')] if isinstance(municipality, str) else [municipality]
        municipalities = [m for m in municipalities if m]
        if municipalities:
            if len(municipalities) == 1:
                municipality_clean = municipalities[0]
                query = query.filter(
                    or_(
                        Property.municipality == municipality_clean,
                        Property.municipality.ilike(f"%{municipality_clean}%")
                    )
                )
            else:
                municipality_filters = []
                for m in municipalities:
                    municipality_clean = m.strip()
                    municipality_filters.append(
                        or_(
                            Property.municipality == municipality_clean,
                            Property.municipality.ilike(f"%{municipality_clean}%")
                        )
                    )
                query = query.filter(or_(*municipality_filters))
    
    # Unit type filter
    if unit_type:
        unit_types = [ut.strip() for ut in unit_type.split(',')] if isinstance(unit_type, str) else [unit_type]
        unit_type_filters = []
        for ut in unit_types:
            if not ut:
                continue
            parts = ut.split(" - ", 1)
            parsed_property_type = parts[0].strip() if parts else None
            parsed_land_use = parts[1].strip() if len(parts) > 1 and parts[1] else None
            filters = []
            if parsed_property_type:
                filters.append(Property.property_type.ilike(f"%{parsed_property_type}%"))
            if parsed_land_use:
                filters.append(Property.land_use.ilike(f"%{parsed_land_use}%"))
            if len(filters) == 2:
                unit_type_filters.append(and_(*filters))
            elif len(filters) == 1:
                unit_type_filters.append(filters[0])
        if unit_type_filters:
            if len(unit_type_filters) == 1:
                query = query.filter(unit_type_filters[0])
            else:
                query = query.filter(or_(*unit_type_filters))
    
    # Zoning filter
    if zoning:
        zoning_codes = [zc.strip() for zc in zoning.split(',')] if isinstance(zoning, str) else [zoning]
        zoning_codes = [zc for zc in zoning_codes if zc]
        if zoning_codes:
            if len(zoning_codes) == 1:
                query = query.filter(Property.zoning.ilike(f"%{zoning_codes[0]}%"))
            else:
                zoning_filters = [Property.zoning.ilike(f"%{zc}%") for zc in zoning_codes]
                query = query.filter(or_(*zoning_filters))
    
    # Property age filter (year built)
    if year_built_min is not None:
        query = query.filter(Property.year_built >= year_built_min)
    if year_built_max is not None:
        query = query.filter(Property.year_built <= year_built_max)
    
    # Time since sale filter
    if time_since_sale:
        from datetime import date, timedelta
        today = date.today()
        if time_since_sale == "Last 2 Years":
            cutoff_date = today - timedelta(days=730)
            query = query.filter(Property.last_sale_date >= cutoff_date)
        elif time_since_sale == "2-5 Years Ago":
            cutoff_date_min = today - timedelta(days=1825)  # 5 years
            cutoff_date_max = today - timedelta(days=730)    # 2 years
            query = query.filter(
                Property.last_sale_date >= cutoff_date_min,
                Property.last_sale_date < cutoff_date_max
            )
        elif time_since_sale == "5-10 Years Ago":
            cutoff_date_min = today - timedelta(days=3650)  # 10 years
            cutoff_date_max = today - timedelta(days=1825)  # 5 years
            query = query.filter(
                Property.last_sale_date >= cutoff_date_min,
                Property.last_sale_date < cutoff_date_max
            )
        elif time_since_sale == "10-20 Years Ago":
            cutoff_date_min = today - timedelta(days=7300)  # 20 years
            cutoff_date_max = today - timedelta(days=3650)  # 10 years
            query = query.filter(
                Property.last_sale_date >= cutoff_date_min,
                Property.last_sale_date < cutoff_date_max
            )
        elif time_since_sale == "20+ Years Ago":
            cutoff_date = today - timedelta(days=7300)  # 20 years
            query = query.filter(Property.last_sale_date < cutoff_date)
        elif time_since_sale == "Never Sold":
            query = query.filter(Property.last_sale_date.is_(None))
    
    # Annual tax filter
    if annual_tax:
        if annual_tax == "Under $2,000":
            query = query.filter(
                or_(
                    Property.tax_amount < 2000,
                    Property.tax_amount.is_(None)
                )
            )
        elif annual_tax == "$2,000 - $5,000":
            query = query.filter(
                and_(
                    Property.tax_amount >= 2000,
                    Property.tax_amount < 5000
                )
            )
        elif annual_tax == "$5,000 - $10,000":
            query = query.filter(
                and_(
                    Property.tax_amount >= 5000,
                    Property.tax_amount < 10000
                )
            )
        elif annual_tax == "$10,000 - $20,000":
            query = query.filter(
                and_(
                    Property.tax_amount >= 10000,
                    Property.tax_amount < 20000
                )
            )
        elif annual_tax == "$20,000+":
            query = query.filter(Property.tax_amount >= 20000)
    
    return query

@router.get("/zoning/options", response_model=ZoningOptionsResponse)
async def get_zoning_options(
    municipality: Optional[str] = Query(None, description="Filter by municipality"),
    unit_type: Optional[str] = Query(None, description="Filter by unit type (property_type - land_use)"),
    property_age: Optional[str] = Query(None, description="Filter by property age range"),
    time_since_sale: Optional[str] = Query(None, description="Filter by time since sale"),
    annual_tax: Optional[str] = Query(None, description="Filter by annual tax range"),
    owner_city: Optional[str] = Query(None, description="Filter by owner mailing city"),
    owner_state: Optional[str] = Query(None, description="Filter by owner mailing state"),
    db: Session = Depends(get_db)
):
    """Get unique zoning codes, optionally filtered by other selections"""
    try:
        # Build query on full Property table to allow filtering
        query = db.query(Property).filter(Property.zoning.isnot(None))
        
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
            year_built_min=year_built_min,
            year_built_max=year_built_max,
            time_since_sale=time_since_sale,
            annual_tax=annual_tax,
            owner_city=owner_city,
            owner_state=owner_state
        )
        
        # Execute query with error handling
        try:
            properties = query.all()
        except Exception as query_error:
            import traceback
            error_details = f"Database query error in get_zoning_options: {str(query_error)}"
            print(error_details)
            traceback.print_exc()
            from fastapi import HTTPException
            raise HTTPException(
                status_code=500,
                detail=f"Failed to query zoning options: {str(query_error)}"
            )
        
        # Extract unique zoning codes from properties
        zoning_codes = set()
        for prop in properties:
            if prop.zoning:
                zoning_codes.add(prop.zoning)
        
        # Sort and return
        zoning_codes = sorted(list(zoning_codes))
        
        return ZoningOptionsResponse(zoning_codes=zoning_codes)
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_msg = f"Error in get_zoning_options: {str(e)}"
        print(error_msg)
        traceback.print_exc()
        from fastapi import HTTPException
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve zoning options: {str(e)}. Check backend logs for details."
        )

@router.get("/unit-types/options", response_model=UnitTypeOptionsResponse)
async def get_unit_type_options(
    municipality: Optional[str] = Query(None, description="Filter by municipality"),
    zoning: Optional[str] = Query(None, description="Filter by zoning code"),
    property_age: Optional[str] = Query(None, description="Filter by property age range"),
    time_since_sale: Optional[str] = Query(None, description="Filter by time since sale"),
    annual_tax: Optional[str] = Query(None, description="Filter by annual tax range"),
    owner_city: Optional[str] = Query(None, description="Filter by owner mailing city"),
    owner_state: Optional[str] = Query(None, description="Filter by owner mailing state"),
    db: Session = Depends(get_db)
):
    """Get unique unit type combinations (property_type + land_use), optionally filtered by other selections"""
    try:
        # Build query on full Property table to allow filtering
        query = db.query(Property).filter(Property.property_type.isnot(None))
        
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
            zoning=zoning,
            year_built_min=year_built_min,
            year_built_max=year_built_max,
            time_since_sale=time_since_sale,
            annual_tax=annual_tax,
            owner_city=owner_city,
            owner_state=owner_state
        )
        
        # Get unique combinations with error handling
        try:
            properties = query.all()
        except Exception as query_error:
            import traceback
            error_details = f"Database query error in get_unit_type_options: {str(query_error)}"
            print(error_details)
            traceback.print_exc()
            from fastapi import HTTPException
            raise HTTPException(
                status_code=500,
                detail=f"Failed to query unit type options: {str(query_error)}"
            )
        
        # Build unique combinations from properties
        unit_type_map = {}
        for prop in properties:
            if prop.property_type:
                key = (prop.property_type, prop.land_use)
                if key not in unit_type_map:
                    unit_type_map[key] = UnitTypeOption(
                        property_type=prop.property_type,
                        land_use=prop.land_use
                    )
        
        unit_types = list(unit_type_map.values())
        
        # Sort by property_type, then by land_use
        unit_types.sort(key=lambda x: (x.property_type or "", x.land_use or ""))
        
        return UnitTypeOptionsResponse(unit_types=unit_types)
    except HTTPException:
        # Re-raise HTTP exceptions (already properly formatted)
        raise
    except Exception as e:
        import traceback
        error_msg = f"Error in get_unit_type_options: {str(e)}"
        print(error_msg)
        traceback.print_exc()
        from fastapi import HTTPException
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve unit type options: {str(e)}. Check backend logs for details."
        )

class MunicipalityBoundsResponse(BaseModel):
    municipality: str
    min_lng: float
    min_lat: float
    max_lng: float
    max_lat: float
    center_lat: float
    center_lng: float
    bbox: str  # Format: "min_lng,min_lat,max_lng,max_lat"

@router.get("/municipality/{municipality}/bounds", response_model=MunicipalityBoundsResponse)
async def get_municipality_bounds(
    municipality: str,
    db: Session = Depends(get_db)
):
    """
    Get the bounding box (extent) of all properties in a municipality.
    Returns min/max lat/lng calculated from property geometries.
    """
    try:
        # Use ST_Extent to get bounding box of all geometries, then extract min/max coordinates
        # ST_Extent returns a box2d, we need to extract the coordinates from it
        extent_result = db.execute(
            text("""
                SELECT 
                    ST_XMin(ST_Extent(geometry)) as min_lng,
                    ST_YMin(ST_Extent(geometry)) as min_lat,
                    ST_XMax(ST_Extent(geometry)) as max_lng,
                    ST_YMax(ST_Extent(geometry)) as max_lat,
                    ST_Y(ST_Centroid(ST_Collect(geometry))) as center_lat,
                    ST_X(ST_Centroid(ST_Collect(geometry))) as center_lng
                FROM properties
                WHERE (municipality = :municipality OR municipality ILIKE :municipality_like)
                  AND geometry IS NOT NULL
            """),
            {
                'municipality': municipality,
                'municipality_like': f"%{municipality}%"
            }
        ).fetchone()
        
        if not extent_result or extent_result[0] is None:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=404,
                detail=f"No properties found for municipality: {municipality}"
            )
        
        min_lng = float(extent_result[0])
        min_lat = float(extent_result[1])
        max_lng = float(extent_result[2])
        max_lat = float(extent_result[3])
        center_lat = float(extent_result[4]) if extent_result[4] is not None else (min_lat + max_lat) / 2
        center_lng = float(extent_result[5]) if extent_result[5] is not None else (min_lng + max_lng) / 2
        
        bbox_str = f"{min_lng},{min_lat},{max_lng},{max_lat}"
        
        return MunicipalityBoundsResponse(
            municipality=municipality,
            min_lng=min_lng,
            min_lat=min_lat,
            max_lng=max_lng,
            max_lat=max_lat,
            center_lat=center_lat,
            center_lng=center_lng,
            bbox=bbox_str
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_msg = f"Error in get_municipality_bounds: {str(e)}"
        print(error_msg)
        traceback.print_exc()
        from fastapi import HTTPException
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve municipality bounds: {str(e)}. Check backend logs for details."
        )
