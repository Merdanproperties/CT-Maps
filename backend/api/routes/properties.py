from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List
from database import get_db
from models import Property, Sale, PropertyComment
from pydantic import BaseModel, EmailStr, field_validator
from datetime import date, datetime
import json
import re

router = APIRouter()

class PropertyResponse(BaseModel):
    id: int
    parcel_id: str
    address: Optional[str]
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
    zoning: Optional[str]
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
    stories: Optional[int]
    total_rooms: Optional[int]
    sales_count: int
    days_since_sale: Optional[int]
    additional_data: Optional[dict]
    sales: List[dict] = []
    
    # Tax Information
    tax_amount: Optional[float]
    tax_year: Optional[int]
    tax_exemptions: Optional[str]
    assessment_year: Optional[int]
    
    # Building Exterior Details
    exterior_walls: Optional[str]
    roof_type: Optional[str]
    roof_material: Optional[str]
    foundation_type: Optional[str]
    exterior_finish: Optional[str]
    garage_type: Optional[str]
    garage_spaces: Optional[int]
    
    # Building Interior Details
    interior_finish: Optional[str]
    heating_type: Optional[str]
    cooling_type: Optional[str]
    fireplace_count: Optional[int]

class PropertyUpdateRequest(BaseModel):
    """Request model for updating property details"""
    address: Optional[str] = None
    owner_name: Optional[str] = None
    owner_phone: Optional[str] = None
    owner_email: Optional[str] = None
    owner_address: Optional[str] = None
    owner_city: Optional[str] = None
    owner_state: Optional[str] = None
    assessed_value: Optional[float] = None
    land_value: Optional[float] = None
    building_value: Optional[float] = None
    property_type: Optional[str] = None
    land_use: Optional[str] = None
    zoning: Optional[str] = None
    lot_size_sqft: Optional[float] = None
    building_area_sqft: Optional[float] = None
    year_built: Optional[int] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[float] = None
    stories: Optional[int] = None
    total_rooms: Optional[int] = None
    tax_amount: Optional[float] = None
    tax_year: Optional[int] = None
    tax_exemptions: Optional[str] = None
    exterior_walls: Optional[str] = None
    roof_type: Optional[str] = None
    roof_material: Optional[str] = None
    foundation_type: Optional[str] = None
    exterior_finish: Optional[str] = None
    garage_type: Optional[str] = None
    garage_spaces: Optional[int] = None
    interior_finish: Optional[str] = None
    heating_type: Optional[str] = None
    cooling_type: Optional[str] = None
    fireplace_count: Optional[int] = None
    is_absentee: Optional[int] = None
    is_vacant: Optional[int] = None
    
    @field_validator('owner_email')
    @classmethod
    def validate_email(cls, v):
        if v is not None and v.strip() != '':
            # Basic email validation
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, v):
                raise ValueError('Invalid email format')
        return v
    
    @field_validator('owner_phone')
    @classmethod
    def validate_phone(cls, v):
        if v is not None and v.strip() != '':
            # Remove common phone formatting characters
            cleaned = re.sub(r'[^\d]', '', v)
            if len(cleaned) < 10 or len(cleaned) > 15:
                raise ValueError('Phone number must be 10-15 digits')
        return v
    
    @field_validator('year_built')
    @classmethod
    def validate_year_built(cls, v):
        if v is not None:
            if v < 1800 or v > 2100:
                raise ValueError('Year built must be between 1800 and 2100')
        return v

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
            zoning=property.zoning,
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
            stories=property.stories,
            total_rooms=property.total_rooms,
            sales_count=property.sales_count or 0,
            days_since_sale=property.days_since_sale,
            additional_data=property.additional_data,
            # Tax Information
            tax_amount=property.tax_amount,
            tax_year=property.tax_year,
            tax_exemptions=property.tax_exemptions,
            assessment_year=property.assessment_year,
            # Building Exterior Details
            exterior_walls=property.exterior_walls,
            roof_type=property.roof_type,
            roof_material=property.roof_material,
            foundation_type=property.foundation_type,
            exterior_finish=property.exterior_finish,
            garage_type=property.garage_type,
            garage_spaces=property.garage_spaces,
            # Building Interior Details
            interior_finish=property.interior_finish,
            heating_type=property.heating_type,
            cooling_type=property.cooling_type,
            fireplace_count=property.fireplace_count,
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
        query = query.filter(func.lower(func.trim(Property.municipality)) == municipality.strip().lower())
    
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
                municipality=prop.municipality,
                zip_code=prop.zip_code,
                owner_name=prop.owner_name,
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
            print(f"Error processing property {prop.id}: {e}")
            continue
    
    return results

@router.patch("/{property_id}", response_model=PropertyDetailResponse)
async def update_property(
    property_id: int,
    update_data: PropertyUpdateRequest,
    db: Session = Depends(get_db)
):
    """Update property details"""
    property = db.query(Property).filter(Property.id == property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")
    
    try:
        # Update only provided fields (exclude_unset=True)
        update_dict = update_data.model_dump(exclude_unset=True)
        
        # Update fields
        for key, value in update_dict.items():
            setattr(property, key, value)
        
        # Update last_updated timestamp
        property.last_updated = date.today()
        
        # Commit changes
        db.commit()
        db.refresh(property)
        
        # Return updated property using same logic as get_property
        return await get_property(property_id, db)
        
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Validation error: {str(e)}")
    except Exception as e:
        db.rollback()
        import traceback
        print(f"Error updating property {property_id}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error updating property: {str(e)}")

# Comment models and endpoints
class CommentCreate(BaseModel):
    comment: str
    
    @field_validator('comment')
    @classmethod
    def validate_comment(cls, v):
        if not v or not v.strip():
            raise ValueError('Comment cannot be empty')
        if len(v.strip()) > 5000:
            raise ValueError('Comment cannot exceed 5000 characters')
        return v.strip()

class CommentResponse(BaseModel):
    id: int
    property_id: int
    comment: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

@router.get("/{property_id}/comments", response_model=List[CommentResponse])
async def get_property_comments(
    property_id: int,
    db: Session = Depends(get_db)
):
    """Get all comments for a property, ordered by created_at (newest first)"""
    # Verify property exists
    property = db.query(Property).filter(Property.id == property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")
    
    # Get comments ordered by created_at descending (newest first)
    comments = db.query(PropertyComment).filter(
        PropertyComment.property_id == property_id
    ).order_by(PropertyComment.created_at.desc()).all()
    
    return comments

@router.post("/{property_id}/comments", response_model=CommentResponse)
async def create_property_comment(
    property_id: int,
    comment_data: CommentCreate,
    db: Session = Depends(get_db)
):
    """Create a new comment for a property"""
    # Verify property exists
    property = db.query(Property).filter(Property.id == property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")
    
    try:
        # Create new comment
        new_comment = PropertyComment(
            property_id=property_id,
            comment=comment_data.comment
        )
        
        db.add(new_comment)
        db.commit()
        db.refresh(new_comment)
        
        return new_comment
        
    except Exception as e:
        db.rollback()
        import traceback
        print(f"Error creating comment for property {property_id}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error creating comment: {str(e)}")

@router.put("/{property_id}/comments/{comment_id}", response_model=CommentResponse)
async def update_property_comment(
    property_id: int,
    comment_id: int,
    comment_data: CommentCreate,
    db: Session = Depends(get_db)
):
    """Update an existing comment"""
    # Verify property exists
    property = db.query(Property).filter(Property.id == property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")
    
    # Verify comment exists and belongs to property
    comment = db.query(PropertyComment).filter(
        PropertyComment.id == comment_id,
        PropertyComment.property_id == property_id
    ).first()
    
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    try:
        # Update comment
        comment.comment = comment_data.comment
        # updated_at is automatically updated by the model
        
        db.commit()
        db.refresh(comment)
        
        return comment
        
    except Exception as e:
        db.rollback()
        import traceback
        print(f"Error updating comment {comment_id} for property {property_id}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error updating comment: {str(e)}")
