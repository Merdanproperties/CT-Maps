"""
Import missing Torrington parcels from geodatabase that weren't imported before
Specifically targets parcels in the 125/2/ area that might be 295 East Main Street
"""
import sys
from pathlib import Path
from datetime import date
import geopandas as gpd
from sqlalchemy import text
from dotenv import load_dotenv
from multiprocessing import Pool, cpu_count

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from models import Property, Base
from database import engine, SessionLocal

load_dotenv()

GDB_PATH = "/Users/jacobmermelstein/Desktop/CT Maps/2025 Parcel Layer.gdb"
MUNICIPALITY = "Torrington"

def process_geodb_chunk_worker(args):
    """Process a chunk of geodatabase records"""
    chunk_data, source_crs = args
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent.parent))
    from database import SessionLocal
    from models import Property
    from geopandas import GeoSeries
    from shapely import wkt
    import pandas as pd
    
    db = SessionLocal()
    properties = []
    
    try:
        for row_data in chunk_data:
            try:
                parcel_id = str(row_data.get('Parcel_ID', '')).strip()
                if not parcel_id:
                    continue
                
                # Check if already exists
                existing = db.query(Property).filter(Property.parcel_id == parcel_id).first()
                if existing:
                    continue
                
                # Convert geometry
                geom = row_data.get('geometry')
                if geom is None:
                    continue
                
                try:
                    geom_series = GeoSeries([geom], crs=source_crs)
                    geom_wgs84 = geom_series.to_crs('EPSG:4326').iloc[0]
                    geom_2d = wkt.loads(wkt.dumps(geom_wgs84, output_dimension=2))
                    if geom_2d is None:
                        continue
                    geometry_wkt = geom_2d.wkt
                    if not geometry_wkt or len(geometry_wkt) < 10:
                        continue
                except Exception:
                    continue
                
                # Map to property fields
                location = str(row_data.get('Location', '')).strip() if pd.notna(row_data.get('Location')) else None
                if location == 'None':
                    location = None
                town_name = str(row_data.get('Town_Name', ''))
                unit_type = str(row_data.get('Unit_Type', ''))
                cama_link = str(row_data.get('CAMA_Link', '')).strip() if pd.notna(row_data.get('CAMA_Link')) else None
                shape_area = float(row_data.get('Shape_Area', 0) or 0)
                
                property_data = {
                    'parcel_id': parcel_id,
                    'address': location,
                    'city': town_name,
                    'municipality': town_name,
                    'zip_code': None,
                    'owner_name': None,
                    'assessed_value': None,
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
                
                properties.append(property_data)
            except Exception as e:
                print(f"Error processing parcel {row_data.get('Parcel_ID', 'unknown')}: {e}")
                continue
    finally:
        db.close()
    
    return properties

def import_missing_parcels():
    """Import missing Torrington parcels"""
    print("=" * 60)
    print("Importing Missing Torrington Parcels")
    print("=" * 60)
    
    # Read geodatabase
    print("\nReading geodatabase...")
    gdf = gpd.read_file(GDB_PATH, layer='Full_State_Parcels_25', driver='FileGDB')
    torrington_gdf = gdf[gdf['Town_Name'].str.contains('Torrington', case=False, na=False)]
    print(f"  Found {len(torrington_gdf):,} Torrington properties in geodatabase")
    
    # Get existing parcel IDs
    print("\nChecking existing properties...")
    db = SessionLocal()
    try:
        existing_parcels = set()
        for prop in db.query(Property.parcel_id).filter(Property.municipality.ilike('%Torrington%')).all():
            if prop.parcel_id:
                existing_parcels.add(str(prop.parcel_id).strip())
        print(f"  Found {len(existing_parcels):,} existing properties")
    finally:
        db.close()
    
    # Filter to missing properties
    missing_properties = []
    for idx, row in torrington_gdf.iterrows():
        parcel_id = str(row.get('Parcel_ID', '')).strip()
        if parcel_id and parcel_id not in existing_parcels:
            missing_properties.append({
                'Parcel_ID': parcel_id,
                'Location': row.get('Location'),
                'Town_Name': row.get('Town_Name'),
                'Unit_Type': row.get('Unit_Type'),
                'CAMA_Link': row.get('CAMA_Link'),
                'Shape_Area': row.get('Shape_Area'),
                'geometry': row.geometry
            })
    
    print(f"  Found {len(missing_properties):,} missing properties to import")
    
    if len(missing_properties) == 0:
        print("\n✅ All properties already imported!")
        return 0
    
    # Parallel processing
    num_workers = cpu_count()
    chunk_size = max(100, len(missing_properties) // num_workers)
    chunks = [missing_properties[i:i+chunk_size] for i in range(0, len(missing_properties), chunk_size)]
    source_crs = torrington_gdf.crs or 'EPSG:6434'
    
    print(f"\nProcessing {len(chunks)} chunks with {num_workers} workers...")
    
    with Pool(num_workers) as pool:
        chunk_args = [(chunk, source_crs) for chunk in chunks]
        results = pool.map(process_geodb_chunk_worker, chunk_args)
    
    # Flatten results
    all_properties = []
    for result in results:
        all_properties.extend(result)
    
    print(f"  Prepared {len(all_properties):,} properties for import")
    
    # Filter out duplicates that might have been added during parallel processing
    if len(all_properties) > 0:
        print(f"\nFiltering duplicates...")
        
        # First, deduplicate within the batch itself
        seen_parcels = set()
        deduplicated = []
        for p in all_properties:
            parcel_id = str(p['parcel_id']).strip()
            if parcel_id not in seen_parcels:
                seen_parcels.add(parcel_id)
                deduplicated.append(p)
        print(f"  Removed {len(all_properties) - len(deduplicated):,} duplicates within batch")
        
        db = SessionLocal()
        try:
            # Get all existing parcel IDs again
            existing_parcels = set()
            for prop in db.query(Property.parcel_id).filter(Property.municipality.ilike('%Torrington%')).all():
                if prop.parcel_id:
                    existing_parcels.add(str(prop.parcel_id).strip())
            
            # Filter out properties that already exist in database
            new_properties = [p for p in deduplicated if str(p['parcel_id']).strip() not in existing_parcels]
            print(f"  Filtered from {len(deduplicated):,} to {len(new_properties):,} new properties")
        finally:
            db.close()
        
        # Bulk insert
        if len(new_properties) > 0:
            print(f"\nInserting {len(new_properties):,} properties...")
            db = SessionLocal()
            try:
                db.bulk_insert_mappings(Property, new_properties)
                db.commit()
                print(f"✅ Successfully imported {len(new_properties):,} properties")
            except Exception as e:
                db.rollback()
                print(f"❌ Error during bulk insert: {e}")
                raise
            finally:
                db.close()
        else:
            print("\n✅ All properties already exist in database")
    
    return len(all_properties)

if __name__ == "__main__":
    import_missing_parcels()
