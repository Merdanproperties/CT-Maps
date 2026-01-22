from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List
from database import get_db
from models import Property, Sale
from pydantic import BaseModel
from datetime import date
import json

router = APIRouter()

class PropertyResponse(BaseModel):
    id: int
    parcel_id: str
    address: Optional[str]
    city: Optional[str]
    municipality: Optional[str]
    zip_code: Optional[str]
    owner_name: Optional[str]
    owner_phone: Optional[str]
    owner_email: Optional[str]
    assessed_value: Optional[float]
    land_value: Optional[float]
    building_value: Optional[float]
    property_type: Optional[str]
    land_use: Optional[str]
    lot_size_sqft: Optional[float]
    year_built: Optional[int]
    last_sale_date: Optional[date]
    last_sale_price: Optional[float]
    is_absentee: int
    is_vacant: int
    equity_estimate: Optional[float]
    geometry: dict
    
    class Config:
        from_attributes = True

class PropertyDetailResponse(PropertyResponse):
    # Note: owner_phone and owner_email are inherited from PropertyResponse, don't redefine them
    owner_address: Optional[str]
    owner_city: Optional[str]
    owner_state: Optional[str]
    building_area_sqft: Optional[float]
    bedrooms: Optional[int]
    bathrooms: Optional[float]
    sales_count: int
    days_since_sale: Optional[int]
    additional_data: Optional[dict]
    sales: List[dict] = []

@router.get("/{property_id}", response_model=PropertyDetailResponse)
async def get_property(property_id: int, db: Session = Depends(get_db)):
    """Get detailed information about a specific property"""
    property = db.query(Property).filter(Property.id == property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")
    
    # Get sales history
    sales = db.query(Sale).filter(Sale.property_id == property_id).order_by(Sale.sale_date.desc()).all()
    
    # Convert geometry to GeoJSON
    try:
        geom_result = db.execute(
            func.ST_AsGeoJSON(property.geometry)
        ).scalar()
        
        # Create response object manually to avoid from_orm issues
        result = PropertyDetailResponse(
            id=property.id,
            parcel_id=property.parcel_id,
            address=property.address,
            city=property.city,
            municipality=property.municipality,
            zip_code=property.zip_code,
            owner_name=property.owner_name,
            owner_phone=property.owner_phone,
            owner_email=property.owner_email,
            assessed_value=property.assessed_value,
            land_value=property.land_value,
            building_value=property.building_value,
            property_type=property.property_type,
            land_use=property.land_use,
            lot_size_sqft=property.lot_size_sqft,
            year_built=property.year_built,
            last_sale_date=property.last_sale_date,
            last_sale_price=property.last_sale_price,
            is_absentee=property.is_absentee or 0,
            is_vacant=property.is_vacant or 0,
            equity_estimate=property.equity_estimate,
            owner_address=property.owner_address,
            owner_city=property.owner_city,
            owner_state=property.owner_state,
            building_area_sqft=property.building_area_sqft,
            bedrooms=property.bedrooms,
            bathrooms=property.bathrooms,
            sales_count=property.sales_count or 0,
            days_since_sale=property.days_since_sale,
            additional_data=property.additional_data,
            geometry={"type": "Feature", "geometry": json.loads(geom_result) if geom_result else None}
        )
    except Exception as e:
        import traceback
        print(f"Error processing property {property.id}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error processing property: {str(e)}")
    result.sales = [
        {
            "sale_date": sale.sale_date.isoformat() if sale.sale_date else None,
            "sale_price": sale.sale_price,
            "buyer_name": sale.buyer_name,
            "seller_name": sale.seller_name,
            "deed_type": sale.deed_type
        }
        for sale in sales
    ]
    
    return result

@router.get("/parcel/{parcel_id}", response_model=PropertyDetailResponse)
async def get_property_by_parcel(parcel_id: str, db: Session = Depends(get_db)):
    """Get property by parcel ID"""
    property = db.query(Property).filter(Property.parcel_id == parcel_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")
    
    return await get_property(property.id, db)

@router.get("/", response_model=List[PropertyResponse])
async def list_properties(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    municipality: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List properties with pagination"""
    query = db.query(Property)
    
    if municipality:
        query = query.filter(Property.municipality.ilike(f"%{municipality}%"))
    
    properties = query.offset(skip).limit(limit).all()
    
    results = []
    for prop in properties:
        try:
            geom_result = db.execute(
                func.ST_AsGeoJSON(prop.geometry)
            ).scalar()
            
            # Create response object manually to avoid from_orm issues
            result = PropertyResponse(
                id=prop.id,
                parcel_id=prop.parcel_id,
                address=prop.address,
                city=prop.city,
                municipality=prop.municipality,
                zip_code=prop.zip_code,
                owner_name=prop.owner_name,
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
                geometry={"type": "Feature", "geometry": json.loads(geom_result) if geom_result else None}
            )
            results.append(result)
        except Exception as e:
            print(f"Error processing property {prop.id}: {e}")
            continue
    
    return results
