from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_
from typing import Optional, List
from database import get_db
from models import Property
from api.routes.properties import PropertyResponse
from pydantic import BaseModel
from datetime import date, timedelta
import json

router = APIRouter()

class FilterResponse(BaseModel):
    properties: List[PropertyResponse]
    total: int
    filter_type: str

@router.get("/high-equity", response_model=FilterResponse)
async def high_equity_properties(
    min_equity: float = Query(50000, description="Minimum equity in dollars"),
    min_equity_percent: Optional[float] = Query(None, description="Minimum equity percentage"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """Find properties with high equity (assessment value significantly higher than last sale price)"""
    query = db.query(Property).filter(
        Property.equity_estimate.isnot(None),
        Property.equity_estimate >= min_equity
    )
    
    if min_equity_percent and min_equity_percent > 0:
        # Filter by percentage if last sale price exists
        query = query.filter(
            or_(
                Property.last_sale_price.is_(None),
                func.abs(Property.assessed_value - Property.last_sale_price) / Property.last_sale_price * 100 >= min_equity_percent
            )
        )
    
    total = query.count()
    skip = (page - 1) * page_size
    properties = query.order_by(Property.equity_estimate.desc()).offset(skip).limit(page_size).all()
    
    results = _format_properties(properties, db)
    
    return FilterResponse(
        properties=results,
        total=total,
        filter_type="high_equity"
    )

@router.get("/vacant", response_model=FilterResponse)
async def vacant_properties(
    include_lots: bool = Query(True, description="Include vacant lots"),
    include_structures: bool = Query(True, description="Include vacant structures"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """Find vacant properties (lots or structures)"""
    conditions = []
    
    if include_lots:
        conditions.append(
            and_(
                Property.is_vacant == 1,
                or_(
                    Property.building_area_sqft.is_(None),
                    Property.building_area_sqft == 0
                )
            )
        )
    
    if include_structures:
        conditions.append(
            and_(
                Property.is_vacant == 1,
                Property.building_area_sqft.isnot(None),
                Property.building_area_sqft > 0
            )
        )
    
    if not conditions:
        return FilterResponse(properties=[], total=0, filter_type="vacant")
    
    query = db.query(Property).filter(or_(*conditions))
    
    total = query.count()
    skip = (page - 1) * page_size
    properties = query.offset(skip).limit(page_size).all()
    
    results = _format_properties(properties, db)
    
    return FilterResponse(
        properties=results,
        total=total,
        filter_type="vacant"
    )

@router.get("/absentee-owners", response_model=FilterResponse)
async def absentee_owner_properties(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """Find properties with absentee owners (owner address differs from property address)"""
    query = db.query(Property).filter(Property.is_absentee == 1)
    
    total = query.count()
    skip = (page - 1) * page_size
    properties = query.offset(skip).limit(page_size).all()
    
    results = _format_properties(properties, db)
    
    return FilterResponse(
        properties=results,
        total=total,
        filter_type="absentee_owners"
    )

@router.get("/recently-sold", response_model=FilterResponse)
async def recently_sold_properties(
    days: int = Query(365, description="Number of days to look back"),
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """Find properties sold within the specified number of days"""
    cutoff_date = date.today() - timedelta(days=days)
    
    query = db.query(Property).filter(
        Property.last_sale_date.isnot(None),
        Property.last_sale_date >= cutoff_date
    )
    
    if min_price:
        query = query.filter(Property.last_sale_price >= min_price)
    if max_price:
        query = query.filter(Property.last_sale_price <= max_price)
    
    total = query.count()
    skip = (page - 1) * page_size
    properties = query.order_by(Property.last_sale_date.desc()).offset(skip).limit(page_size).all()
    
    results = _format_properties(properties, db)
    
    return FilterResponse(
        properties=results,
        total=total,
        filter_type="recently_sold"
    )

@router.get("/low-equity", response_model=FilterResponse)
async def low_equity_properties(
    max_equity: float = Query(10000, description="Maximum equity in dollars"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """Find properties with low equity (potentially underwater)"""
    query = db.query(Property).filter(
        Property.last_sale_price.isnot(None),
        Property.assessed_value.isnot(None),
        Property.assessed_value - Property.last_sale_price <= max_equity
    )
    
    total = query.count()
    skip = (page - 1) * page_size
    properties = query.order_by(Property.assessed_value - Property.last_sale_price).offset(skip).limit(page_size).all()
    
    results = _format_properties(properties, db)
    
    return FilterResponse(
        properties=results,
        total=total,
        filter_type="low_equity"
    )

def _format_properties(properties, db):
    """Helper function to format properties with geometry"""
    results = []
    for prop in properties:
        try:
            geom_result = db.execute(
                func.ST_AsGeoJSON(prop.geometry)
            ).scalar()
            
            # Create response object manually to avoid from_orm issues (Pydantic v2)
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
                geometry={"type": "Feature", "geometry": json.loads(geom_result) if geom_result else None}
            )
            results.append(result)
        except Exception as e:
            import traceback
            print(f"Error processing property {prop.id if prop else 'unknown'}: {e}")
            traceback.print_exc()
            continue
    
    return results
