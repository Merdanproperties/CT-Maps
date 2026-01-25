"""
Import Torrington properties from geodatabase
Only imports properties that don't already exist in the database
"""
import sys
from pathlib import Path
from datetime import date
import geopandas as gpd
from sqlalchemy import text
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from models import Property, Base
from database import engine, SessionLocal

load_dotenv()

GDB_PATH = "/Users/jacobmermelstein/Desktop/CT Maps/2025 Parcel Layer.gdb"
MUNICIPALITY = "Torrington"

def import_torrington_properties(gdb_path: str, batch_size: int = 500):
    """
    Import Torrington properties from geodatabase
    """
    print("=" * 60)
    print("Importing Torrington Properties from Geodatabase")
    print("=" * 60)
    
    # Get existing parcel IDs from database
    print("\n1. Checking existing Torrington properties in database...")
    db = SessionLocal()
    try:
        existing_parcels = set()
        for prop in db.query(Property.parcel_id).filter(Property.municipality.ilike('%Torrington%')).all():
            if prop.parcel_id:
                existing_parcels.add(str(prop.parcel_id).strip())
        print(f"   Found {len(existing_parcels):,} existing Torrington properties")
    finally:
        db.close()
    
    # Read geodatabase
    print("\n2. Reading Torrington properties from geodatabase...")
    gdf = gpd.read_file(gdb_path, layer='Full_State_Parcels_25', driver='FileGDB')
    torrington_gdf = gdf[gdf['Town_Name'].str.contains('Torrington', case=False, na=False)]
    print(f"   Found {len(torrington_gdf):,} Torrington properties in geodatabase")
    
    # Filter to only missing properties
    print("\n3. Filtering to missing properties...")
    missing_properties = []
    for idx, row in torrington_gdf.iterrows():
        parcel_id = str(row.get('Parcel_ID', '')).strip()
        if parcel_id and parcel_id not in existing_parcels:
            missing_properties.append((idx, row))
    
    print(f"   Found {len(missing_properties):,} missing properties to import")
    
    if len(missing_properties) == 0:
        print("\n✅ All Torrington properties already in database!")
        return
    
    # Process in batches
    print(f"\n4. Importing {len(missing_properties):,} properties in batches of {batch_size}...")
    db = SessionLocal()
    imported = 0
    errors = 0
    total_batches = (len(missing_properties) + batch_size - 1) // batch_size
    
    try:
        for batch_num, batch_idx in enumerate(range(0, len(missing_properties), batch_size), 1):
            batch = missing_properties[batch_idx:batch_idx+batch_size]
            
            print(f"\n   Processing batch {batch_num}/{total_batches} ({batch_idx+1}-{min(batch_idx+batch_size, len(missing_properties))} of {len(missing_properties)})...")
            
            for idx, row in batch:
                try:
                    parcel_id = str(row.get('Parcel_ID', '')).strip()
                    
                    # Skip if no parcel_id
                    if not parcel_id:
                        continue
                    
                    # Check if already exists in database (check each one individually)
                    existing = db.query(Property).filter(Property.parcel_id == parcel_id).first()
                    if existing:
                        continue  # Skip if already exists
                    
                    # Check geometry
                    geom = row.geometry
                    if geom is None:
                        errors += 1
                        continue
                    
                    # Convert geometry
                    source_crs = torrington_gdf.crs or 'EPSG:6434'
                    try:
                        from geopandas import GeoSeries
                        from shapely import wkt
                        geom_series = GeoSeries([geom], crs=source_crs)
                        geom_wgs84 = geom_series.to_crs('EPSG:4326').iloc[0]
                        geom_2d = wkt.loads(wkt.dumps(geom_wgs84, output_dimension=2))
                        if geom_2d is None:
                            errors += 1
                            continue
                        geometry_wkt = geom_2d.wkt
                        if not geometry_wkt or len(geometry_wkt) < 10:
                            errors += 1
                            continue
                    except Exception:
                        errors += 1
                        continue
                    
                    # Map to property fields
                    location = str(row.get('Location', ''))
                    town_name = str(row.get('Town_Name', ''))
                    unit_type = str(row.get('Unit_Type', ''))
                    cama_link = str(row.get('CAMA_Link', ''))
                    shape_area = float(row.get('Shape_Area', 0) or 0)
                    
                    property_data = {
                        'parcel_id': parcel_id,
                        'address': location,
                        'city': town_name,
                        'municipality': town_name,
                        'zip_code': None,
                        'owner_name': None,  # Will be filled by CAMA import
                        'owner_address': None,
                        'owner_city': None,
                        'owner_state': 'CT',
                        'owner_zip': None,
                        'assessed_value': None,  # Will be filled by CAMA import
                        'land_value': None,
                        'building_value': None,
                        'total_value': None,
                        'property_type': unit_type,
                        'land_use': None,
                        'lot_size_sqft': shape_area,
                        'building_area_sqft': None,
                        'year_built': None,
                        'data_source': 'CT Parcel Data 2025',
                        'last_updated': date.today(),
                    }
                    
                    # Store CAMA link in additional_data for future joining
                    if cama_link:
                        property_data['additional_data'] = {'cama_link': cama_link}
                    
                    # Add geometry
                    property_data['geometry'] = geometry_wkt
                    
                    # Create property
                    try:
                        prop = Property(**property_data)
                        db.add(prop)
                        db.flush()  # Flush to check for duplicates immediately
                        imported += 1
                    except Exception as flush_error:
                        # Handle duplicate key errors gracefully
                        if 'duplicate' in str(flush_error).lower() or 'unique' in str(flush_error).lower():
                            db.rollback()
                            continue  # Skip this one, continue with next
                        raise  # Re-raise if it's a different error
                    
                except Exception as e:
                    # Handle duplicate key errors gracefully
                    if 'duplicate' in str(e).lower() or 'unique' in str(e).lower() or 'already exists' in str(e).lower():
                        db.rollback()
                        continue  # Property already exists, skip it
                    errors += 1
                    if errors <= 10:
                        print(f"      ⚠️  Error importing {parcel_id}: {e}")
                    db.rollback()
                    continue
            
            # Commit batch
            try:
                db.commit()
                print(f"      ✅ Committed batch {batch_num}: {imported:,} imported, {errors:,} errors")
            except Exception as e:
                db.rollback()
                # Try to identify which property caused the issue and skip it
                if 'duplicate' in str(e).lower() or 'unique' in str(e).lower():
                    print(f"      ⚠️  Duplicate detected in batch {batch_num}, continuing...")
                    # Continue to next batch
                else:
                    print(f"      ⚠️  Error committing batch {batch_num}: {e}")
                    errors += len(batch)
        
        print("\n" + "=" * 60)
        print("Import Summary:")
        print(f"  ✅ Imported: {imported:,}")
        print(f"  ❌ Errors: {errors:,}")
        print("=" * 60)
        
    finally:
        db.close()

if __name__ == "__main__":
    import_torrington_properties(GDB_PATH)
