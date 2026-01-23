from sqlalchemy import Column, Integer, String, Float, Date, Text, Index
from sqlalchemy.dialects.postgresql import JSONB
from geoalchemy2 import Geometry
from database import Base

class Property(Base):
    __tablename__ = "properties"
    
    id = Column(Integer, primary_key=True, index=True)
    parcel_id = Column(String, unique=True, index=True, nullable=False)
    address = Column(String, index=True)
    city = Column(String, index=True)
    municipality = Column(String, index=True)
    zip_code = Column(String)
    
    # Owner information
    owner_name = Column(String, index=True)
    owner_address = Column(String)
    owner_city = Column(String)
    owner_state = Column(String)
    owner_zip = Column(String)
    owner_phone = Column(String)  # Owner phone number
    owner_email = Column(String)  # Owner email address
    is_absentee = Column(Integer, default=0)  # 1 if owner address differs from property address
    
    # Assessment data
    assessed_value = Column(Float)
    land_value = Column(Float)
    building_value = Column(Float)
    total_value = Column(Float)
    assessment_year = Column(Integer)
    
    # Property characteristics
    property_type = Column(String)
    land_use = Column(String)
    lot_size_sqft = Column(Float)
    building_area_sqft = Column(Float)
    year_built = Column(Integer)
    bedrooms = Column(Integer)
    bathrooms = Column(Float)
    stories = Column(Integer)
    total_rooms = Column(Integer)
    
    # Tax Information
    tax_amount = Column(Float)
    tax_year = Column(Integer)
    tax_exemptions = Column(String)
    
    # Building Exterior Details
    exterior_walls = Column(String)
    roof_type = Column(String)
    roof_material = Column(String)
    foundation_type = Column(String)
    exterior_finish = Column(String)
    garage_type = Column(String)
    garage_spaces = Column(Integer)
    
    # Building Interior Details
    interior_finish = Column(String)
    heating_type = Column(String)
    cooling_type = Column(String)
    fireplace_count = Column(Integer)
    
    # Sales data
    last_sale_date = Column(Date)
    last_sale_price = Column(Float)
    sales_count = Column(Integer, default=0)
    
    # Calculated fields for lead generation
    equity_estimate = Column(Float)  # Estimated equity based on assessment vs last sale
    is_vacant = Column(Integer, default=0)  # 1 if vacant lot or vacant structure
    days_since_sale = Column(Integer)
    
    # Geometry (PostGIS) - Using GEOMETRY to support both Polygon and MultiPolygon
    geometry = Column(Geometry('GEOMETRY', srid=4326), nullable=False)
    
    # Additional data stored as JSON
    additional_data = Column(JSONB)
    
    # Metadata
    data_source = Column(String)
    last_updated = Column(Date)
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_property_geometry', 'geometry', postgresql_using='gist'),
        Index('idx_property_municipality', 'municipality'),
        Index('idx_property_assessed_value', 'assessed_value'),
        Index('idx_property_last_sale_date', 'last_sale_date'),
    )

class Sale(Base):
    __tablename__ = "sales"
    
    id = Column(Integer, primary_key=True, index=True)
    parcel_id = Column(String, index=True, nullable=False)
    sale_date = Column(Date, index=True, nullable=False)
    sale_price = Column(Float, nullable=False)
    property_type = Column(String)
    deed_type = Column(String)
    buyer_name = Column(String)
    seller_name = Column(String)
    
    # Link to property
    property_id = Column(Integer, index=True)
    
    __table_args__ = (
        Index('idx_sale_parcel_date', 'parcel_id', 'sale_date'),
    )
