from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import Optional, List
from database import get_db
from models import Property
from api.routes.properties import PropertyResponse
from pydantic import BaseModel
import json

router = APIRouter()

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
            query = query.filter(
                or_(
                    Property.address.ilike(search_term),
                    Property.owner_name.ilike(search_term),
                    Property.parcel_id.ilike(search_term),
                    Property.city.ilike(search_term)
                )
            )
        
        # Municipality filter - try exact match first, then partial
        if municipality:
            # Remove any extra whitespace and try exact match first
            municipality_clean = municipality.strip()
            query = query.filter(
                or_(
                    Property.municipality == municipality_clean,
                    Property.municipality.ilike(f"%{municipality_clean}%")
                )
            )
        
        # Value range filter
        if min_value is not None:
            query = query.filter(Property.assessed_value >= min_value)
        if max_value is not None:
            query = query.filter(Property.assessed_value <= max_value)
        
        # Property type filter (case-insensitive partial match for flexibility)
        if property_type:
            query = query.filter(Property.property_type.ilike(f"%{property_type}%"))
        
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
                geom_result = None
                if prop.geometry is not None:
                    try:
                        geom_result = db.execute(
                            func.ST_AsGeoJSON(prop.geometry)
                        ).scalar()
                    except Exception as geom_error:
                        print(f"Error converting geometry for property {prop.id}: {geom_error}")
                        geom_result = None
                
                # Parse geometry JSON if available
                geometry_data = None
                if geom_result:
                    try:
                        geometry_data = json.loads(geom_result)
                    except json.JSONDecodeError:
                        print(f"Error parsing GeoJSON for property {prop.id}")
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
                print(f"Error processing property {prop.id if prop else 'unknown'}: {e}")
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
        raise HTTPException(status_code=500, detail=error_msg)
