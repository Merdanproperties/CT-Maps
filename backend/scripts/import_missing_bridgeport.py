"""
Import missing Bridgeport properties from geodatabase
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

def import_missing_bridgeport(gdb_path: str, batch_size: int = 500):
    """
    Import only Bridgeport properties that don't exist in database
    """
    print("=" * 60)
    print("Importing Missing Bridgeport Properties from Geodatabase")
    print("=" * 60)
    
    # Get existing parcel IDs from database
    print("\n1. Checking existing Bridgeport properties in database...")
    db = SessionLocal()
    try:
        existing_parcels = set()
        for prop in db.query(Property.parcel_id).filter(Property.municipality.ilike('%Bridgeport%')).all():
            if prop.parcel_id:
                existing_parcels.add(str(prop.parcel_id).strip())
        print(f"   Found {len(existing_parcels):,} existing Bridgeport properties")
    finally:
        db.close()
    
    # Read geodatabase
    print("\n2. Reading Bridgeport properties from geodatabase...")
    gdf = gpd.read_file(gdb_path, layer='Full_State_Parcels_25', driver='FileGDB')
    bridgeport_gdf = gdf[gdf['Town_Name'].str.contains('Bridgeport', case=False, na=False)]
    print(f"   Found {len(bridgeport_gdf):,} Bridgeport properties in geodatabase")
    
    # Filter to only missing properties
    print("\n3. Filtering to missing properties...")
    missing_properties = []
    for idx, row in bridgeport_gdf.iterrows():
        parcel_id = str(row.get('Parcel_ID', '')).strip()
        if parcel_id and parcel_id not in existing_parcels:
            missing_properties.append((idx, row))
    
    print(f"   Found {len(missing_properties):,} missing properties to import")
    
    if len(missing_properties) == 0:
        print("\n✅ All Bridgeport properties are already in the database!")
        return
    
    # Create database tables if needed
    Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
        conn.commit()
    
    # Import missing properties
    print(f"\n4. Importing {len(missing_properties):,} missing properties...")
    db = SessionLocal()
    
    try:
        imported = 0
        errors = 0
        start_time = __import__('datetime').datetime.now()
        
        for batch_idx in range(0, len(missing_properties), batch_size):
            batch = missing_properties[batch_idx:batch_idx + batch_size]
            batch_num = batch_idx // batch_size + 1
            total_batches = (len(missing_properties) + batch_size - 1) // batch_size
            
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
                    source_crs = bridgeport_gdf.crs or 'EPSG:6434'
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
                        'owner_name': None,
                        'owner_address': None,
                        'owner_city': None,
                        'owner_state': 'CT',
                        'property_type': unit_type,
                        'lot_size_sqft': shape_area,
                        'data_source': 'CT Parcel Data 2025',
                        'last_updated': date.today(),
                        'geometry': geometry_wkt,
                        'is_absentee': 0,
                        'is_vacant': 0,
                    }
                    
                    if cama_link:
                        property_data['additional_data'] = {'cama_link': cama_link}
                    
                    # Create new property
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
                    
                    if imported % 100 == 0:
                        elapsed = (__import__('datetime').datetime.now() - start_time).total_seconds()
                        rate = imported / elapsed if elapsed > 0 else 0
                        remaining = (len(missing_properties) - imported) / rate if rate > 0 else 0
                        print(f"      Progress: {imported:,}/{len(missing_properties):,} | "
                              f"Rate: {rate:.1f}/sec | ETA: {remaining/60:.1f} min")
                
                except Exception as e:
                    # Handle duplicate key errors gracefully
                    if 'duplicate' in str(e).lower() or 'unique' in str(e).lower() or 'already exists' in str(e).lower():
                        db.rollback()
                        continue  # Property already exists, skip it
                    errors += 1
                    if errors <= 10:
                        print(f"      Error importing {parcel_id}: {e}")
                    db.rollback()
                    continue
            
            # Commit batch
            try:
                db.commit()
                print(f"      ✅ Committed batch. Imported: {imported:,} | Errors: {errors:,}")
            except Exception as e:
                db.rollback()
                # Try to identify which property caused the issue and skip it
                if 'duplicate' in str(e).lower() or 'unique' in str(e).lower():
                    print(f"      ⚠️  Duplicate detected in batch, continuing...")
                    # Continue to next batch
                else:
                    print(f"      ❌ Error committing batch: {e}")
                    raise
        
        elapsed_total = (__import__('datetime').datetime.now() - start_time).total_seconds()
        print(f"\n{'='*60}")
        print(f"Import Complete!")
        print(f"  ✅ Imported: {imported:,} properties")
        print(f"  ❌ Errors: {errors:,}")
        print(f"  ⏱️  Time: {elapsed_total/60:.1f} minutes")
        print(f"{'='*60}")
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ Error during import: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    gdb_path = Path(__file__).parent.parent.parent / "2025 Parcel Layer.gdb"
    
    if not gdb_path.exists():
        print(f"Error: Geodatabase not found at {gdb_path}")
        sys.exit(1)
    
    import_missing_bridgeport(str(gdb_path))
    print("\n✅ Done! Now run the CAMA import to populate these properties with data.")
