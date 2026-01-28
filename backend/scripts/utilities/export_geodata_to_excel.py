"""
Export Geodata to Excel
Exports all property data with geometry columns (latitude, longitude, WKT) to Excel
"""
import sys
from pathlib import Path
import pandas as pd
from datetime import datetime
from sqlalchemy import func, text

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from database import SessionLocal
from models import Property

def export_geodata_to_excel(limit: int = 1000, municipality: str = None, output_dir: str = None):
    """
    Export geodata to Excel with all columns including geometry
    
    Args:
        limit: Maximum number of properties to export (default: 1000)
        municipality: Filter by municipality name (optional)
        output_dir: Output directory (default: Analysis scripts folder)
    """
    db = SessionLocal()
    
    try:
        print("=" * 80)
        print("EXPORTING GEODATA TO EXCEL")
        print("=" * 80)
        
        # Build query
        query = db.query(
            Property.id,
            Property.parcel_id,
            Property.address,
            Property.municipality,
            Property.zip_code,
            Property.owner_name,
            Property.owner_address,
            Property.owner_city,
            Property.owner_state,
            Property.owner_zip,
            Property.owner_phone,
            Property.owner_email,
            Property.is_absentee,
            Property.assessed_value,
            Property.land_value,
            Property.building_value,
            Property.total_value,
            Property.assessment_year,
            Property.property_type,
            Property.land_use,
            Property.zoning,
            Property.lot_size_sqft,
            Property.building_area_sqft,
            Property.year_built,
            Property.bedrooms,
            Property.bathrooms,
            Property.stories,
            Property.total_rooms,
            Property.tax_amount,
            Property.tax_year,
            Property.tax_exemptions,
            Property.exterior_walls,
            Property.roof_type,
            Property.roof_material,
            Property.foundation_type,
            Property.exterior_finish,
            Property.garage_type,
            Property.garage_spaces,
            Property.interior_finish,
            Property.heating_type,
            Property.cooling_type,
            Property.fireplace_count,
            Property.last_sale_date,
            Property.last_sale_price,
            Property.sales_count,
            Property.equity_estimate,
            Property.is_vacant,
            Property.days_since_sale,
            Property.data_source,
            Property.last_updated,
            Property.additional_data
        )
        
        if municipality:
            query = query.filter(Property.municipality.ilike(f"%{municipality}%"))
        
        properties = query.limit(limit).all()
        
        print(f"\n📊 Found {len(properties):,} properties")
        print(f"   Extracting geometry data...")
        
        # Extract geometry data for each property
        excel_data = []
        for prop in properties:
            # Get geometry coordinates and WKT
            lat = None
            lon = None
            wkt = None
            
            try:
                result = db.execute(text(
                    'SELECT '
                    'ST_Y(ST_Centroid(geometry)) as lat, '
                    'ST_X(ST_Centroid(geometry)) as lon, '
                    'ST_AsText(geometry) as wkt '
                    'FROM properties WHERE id = :id'
                ), {'id': prop.id}).fetchone()
                
                if result:
                    lat = result[0]
                    lon = result[1]
                    wkt = result[2]
            except Exception as e:
                print(f"  ⚠️  Error extracting geometry for property {prop.id}: {e}")
            
            # Build row data
            row = {
                'ID': prop.id,
                'Parcel ID': prop.parcel_id or '',
                'Address': prop.address or '',
                'Municipality': prop.municipality or '',
                'Zip Code': prop.zip_code or '',
                'Owner Name': prop.owner_name or '',
                'Owner Address': prop.owner_address or '',
                'Owner City': prop.owner_city or '',
                'Owner State': prop.owner_state or '',
                'Owner Zip': prop.owner_zip or '',
                'Owner Phone': prop.owner_phone or '',
                'Owner Email': prop.owner_email or '',
                'Is Absentee': 'Yes' if prop.is_absentee == 1 else 'No',
                'Assessed Value': prop.assessed_value if prop.assessed_value else '',
                'Land Value': prop.land_value if prop.land_value else '',
                'Building Value': prop.building_value if prop.building_value else '',
                'Total Value': prop.total_value if prop.total_value else '',
                'Assessment Year': prop.assessment_year if prop.assessment_year else '',
                'Property Type': prop.property_type or '',
                'Land Use': prop.land_use or '',
                'Zoning': prop.zoning or '',
                'Lot Size (sqft)': prop.lot_size_sqft if prop.lot_size_sqft else '',
                'Building Area (sqft)': prop.building_area_sqft if prop.building_area_sqft else '',
                'Year Built': prop.year_built if prop.year_built else '',
                'Bedrooms': prop.bedrooms if prop.bedrooms else '',
                'Bathrooms': prop.bathrooms if prop.bathrooms else '',
                'Stories': prop.stories if prop.stories else '',
                'Total Rooms': prop.total_rooms if prop.total_rooms else '',
                'Tax Amount': prop.tax_amount if prop.tax_amount else '',
                'Tax Year': prop.tax_year if prop.tax_year else '',
                'Tax Exemptions': prop.tax_exemptions or '',
                'Exterior Walls': prop.exterior_walls or '',
                'Roof Type': prop.roof_type or '',
                'Roof Material': prop.roof_material or '',
                'Foundation Type': prop.foundation_type or '',
                'Exterior Finish': prop.exterior_finish or '',
                'Garage Type': prop.garage_type or '',
                'Garage Spaces': prop.garage_spaces if prop.garage_spaces else '',
                'Interior Finish': prop.interior_finish or '',
                'Heating Type': prop.heating_type or '',
                'Cooling Type': prop.cooling_type or '',
                'Fireplace Count': prop.fireplace_count if prop.fireplace_count else '',
                'Last Sale Date': prop.last_sale_date.strftime('%Y-%m-%d') if prop.last_sale_date else '',
                'Last Sale Price': prop.last_sale_price if prop.last_sale_price else '',
                'Sales Count': prop.sales_count if prop.sales_count else '',
                'Equity Estimate': prop.equity_estimate if prop.equity_estimate else '',
                'Is Vacant': 'Yes' if prop.is_vacant == 1 else 'No',
                'Days Since Sale': prop.days_since_sale if prop.days_since_sale else '',
                'Data Source': prop.data_source or '',
                'Last Updated': prop.last_updated.strftime('%Y-%m-%d') if prop.last_updated else '',
                'Additional Data': str(prop.additional_data) if prop.additional_data else '',
                # Geometry columns
                'Latitude': lat if lat else '',
                'Longitude': lon if lon else '',
                'Geometry WKT': wkt if wkt else ''
            }
            
            excel_data.append(row)
        
        # Create DataFrame
        df = pd.DataFrame(excel_data)
        
        # Create output directory
        if output_dir is None:
            workspace_root = Path(__file__).parent.parent.parent.parent
            output_path = workspace_root / "Analysis scripts"
        else:
            output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        municipality_str = f"_{municipality.replace(' ', '_')}" if municipality else ""
        filename = f"geodata_export{municipality_str}_{timestamp}.xlsx"
        filepath = output_path / filename
        
        # Export to Excel
        print(f"\n📝 Exporting to Excel...")
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Properties', index=False)
            
            # Auto-adjust column widths
            worksheet = writer.sheets['Properties']
            for idx, col in enumerate(df.columns, 1):
                max_length = max(
                    df[col].astype(str).map(len).max() if len(df) > 0 else 0,
                    len(str(col))
                )
                # Excel column letter calculation
                if idx <= 26:
                    col_letter = chr(64 + idx)
                else:
                    col_letter = chr(64 + (idx - 1) // 26) + chr(64 + ((idx - 1) % 26) + 1)
                worksheet.column_dimensions[col_letter].width = min(max_length + 2, 50)
        
        print(f"\n✅ Exported {len(excel_data):,} properties to:")
        print(f"   {filepath}")
        
        return str(filepath)
        
    finally:
        db.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Export geodata to Excel')
    parser.add_argument('--limit', type=int, default=1000, help='Maximum number of properties to export')
    parser.add_argument('--municipality', type=str, help='Filter by municipality name')
    parser.add_argument('--output-dir', type=str, help='Output directory (default: Analysis scripts folder)')
    
    args = parser.parse_args()
    
    export_geodata_to_excel(
        limit=args.limit,
        municipality=args.municipality,
        output_dir=args.output_dir
    )
