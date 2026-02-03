"""
Script to process Connecticut parcel geodatabase and import into PostgreSQL
"""
import os
import sys
from pathlib import Path
from datetime import date
import geopandas as gpd
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from models import Property, Base
from database import engine, SessionLocal

load_dotenv()

def process_geodatabase(gdb_path: str, batch_size: int = 1000, limit: int = None):
    """
    Process the geodatabase file and import parcels into the database
    
    Args:
        gdb_path: Path to the geodatabase
        batch_size: Number of parcels to process per batch
        limit: Maximum number of parcels to process (None = all)
    """
    print(f"Reading geodatabase from {gdb_path}...")
    
    # Read the geodatabase
    # Based on inspection, the layer is called 'Full_State_Parcels_25'
    import fiona
    layers_list = fiona.listlayers(gdb_path)
    print(f"Available layers: {layers_list}")
    
    if not layers_list:
        raise Exception("No layers found in geodatabase")
    
    # Use the first layer (usually 'Full_State_Parcels_25')
    layer_name = layers_list[0]
    print(f"Reading layer: {layer_name}")
    
    # Read with limit if specified
    if limit:
        print(f"⚠️  Processing SAMPLE: First {limit:,} parcels only")
        layers = gpd.read_file(gdb_path, layer=layer_name, driver='FileGDB', rows=slice(0, limit))
    else:
        layers = gpd.read_file(gdb_path, layer=layer_name, driver='FileGDB')
    
    print(f"Found {len(layers)} parcels to process")
    if limit:
        print(f"   (Sample mode: processing {len(layers):,} of ~1.28M total parcels)")
    print(f"Columns: {list(layers.columns)}")
    
    # Create database tables
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    
    # Enable PostGIS if not already enabled
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
        conn.commit()
    
    db = SessionLocal()
    
    try:
        # Process in batches
        total = len(layers)
        processed = 0
        
        for i in range(0, total, batch_size):
            batch = layers.iloc[i:i+batch_size]
            print(f"Processing batch {i//batch_size + 1} ({i+1}-{min(i+batch_size, total)} of {total})...")
            
            for idx, row in batch.iterrows():
                try:
                    # First check geometry - skip if None
                    geom = row.geometry
                    if geom is None:
                        continue
                    
                    # Convert geometry early - skip if conversion fails
                    source_crs = layers.crs or 'EPSG:6434'
                    try:
                        from geopandas import GeoSeries
                        from shapely import wkt
                        geom_series = GeoSeries([geom], crs=source_crs)
                        geom_wgs84 = geom_series.to_crs('EPSG:4326').iloc[0]
                        geom_2d = wkt.loads(wkt.dumps(geom_wgs84, output_dimension=2))
                        if geom_2d is None:
                            continue
                        geometry_wkt = geom_2d.wkt
                        if not geometry_wkt or len(geometry_wkt) < 10:  # Basic validation
                            continue
                    except Exception as geom_error:
                        continue  # Skip parcels with geometry errors
                    
                    # Map columns to property fields
                    # Based on actual geodatabase schema from inspection
                    # Note: This geodatabase contains parcel boundaries and basic info
                    # CAMA data (assessments, owners) may be in separate files
                    
                    # Get values with fallbacks
                    parcel_id = str(row.get('Parcel_ID', row.get('Link', row.get('CAMA_Link', idx))))
                    location = str(row.get('Location', ''))
                    town_name = str(row.get('Town_Name', ''))
                    unit_type = str(row.get('Unit_Type', ''))
                    cama_link = str(row.get('CAMA_Link', ''))
                    shape_area = float(row.get('Shape_Area', 0) or 0)
                    
                    property_data = {
                        'parcel_id': parcel_id,
                        'address': location,
                        'municipality': town_name,
                        'zip_code': None,  # Not in this geodatabase
                        'owner_name': None,  # Not in this geodatabase - need CAMA data
                        'owner_address': None,  # Not in this geodatabase
                        'owner_city': None,
                        'owner_state': 'CT',
                        'owner_zip': None,
                        'assessed_value': None,  # Need CAMA data
                        'land_value': None,  # Need CAMA data
                        'building_value': None,  # Need CAMA data
                        'total_value': None,  # Need CAMA data
                        'property_type': unit_type,
                        'land_use': None,  # Not in this geodatabase
                        'lot_size_sqft': shape_area,  # Shape_Area is in square feet
                        'building_area_sqft': None,  # Need CAMA data
                        'year_built': None,  # Need CAMA data
                        'data_source': 'CT Parcel Data 2025',
                        'last_updated': date.today(),
                    }
                    
                    # Store CAMA link in additional_data for future joining
                    if cama_link:
                        property_data['additional_data'] = {'cama_link': cama_link}
                    
                    # Add geometry to property_data BEFORE creating Property object
                    property_data['geometry'] = geometry_wkt
                    
                    # Check if property already exists (in DB or in current batch)
                    existing = db.query(Property).filter(
                        Property.parcel_id == property_data['parcel_id']
                    ).first()
                    
                    if existing:
                        # Update existing property
                        for key, value in property_data.items():
                            if key != 'parcel_id' and value is not None:
                                setattr(existing, key, value)
                        prop = existing
                        # Don't add to session again, just update
                    else:
                        # Check if we've already processed this parcel_id in current batch
                        # (to avoid duplicates within the same batch)
                        try:
                            # Create new property with geometry included
                            prop = Property(**property_data)
                            db.add(prop)
                            db.flush()  # Flush to check for duplicates immediately
                        except Exception as e:
                            if 'duplicate' in str(e).lower() or 'unique' in str(e).lower():
                                # Duplicate found, update existing instead
                                existing = db.query(Property).filter(
                                    Property.parcel_id == property_data['parcel_id']
                                ).first()
                                if existing:
                                    for key, value in property_data.items():
                                        if key != 'parcel_id' and value is not None:
                                            setattr(existing, key, value)
                                else:
                                    print(f"Warning: Duplicate parcel_id {property_data['parcel_id']} but couldn't find existing record")
                                    continue
                            else:
                                raise
                    
                    # Calculate derived fields
                    # Note: Many fields require CAMA data which isn't in this geodatabase
                    
                    # Absentee owner check (will be set when CAMA data is added)
                    prop.is_absentee = 0  # Default, will update with CAMA data
                    
                    # Vacant property check (heuristic based on available data)
                    # If no building area info and property type suggests vacant
                    if unit_type and ('vacant' in unit_type.lower() or 'lot' in unit_type.lower()):
                        prop.is_vacant = 1
                    else:
                        prop.is_vacant = 0  # Default, will update with CAMA data
                    
                    # Equity estimate (requires CAMA data)
                    prop.equity_estimate = None
                    
                    processed += 1
                    if processed % 100 == 0:
                        print(f"  Processed {processed} parcels so far...")
                    
                except Exception as e:
                    if processed % 100 == 0 or "Error" in str(e):
                        print(f"Error processing row {idx}: {e}")
                    db.rollback()  # Rollback on error to continue with next row
                    continue
            
            # Commit batch
            try:
                db.commit()
                print(f"Committed batch. Total processed: {processed}/{total}")
            except Exception as e:
                db.rollback()
                print(f"Error committing batch: {e}")
                raise
        
        print(f"\nSuccessfully processed {processed} properties")
        
    except Exception as e:
        db.rollback()
        print(f"Error during processing: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Process CT parcel geodatabase')
    parser.add_argument('--limit', type=int, help='Limit number of parcels to process (for testing)')
    parser.add_argument('--batch-size', type=int, default=1000, help='Batch size for processing')
    args = parser.parse_args()
    
    # Path to geodatabase
    gdb_path = Path(__file__).parent.parent.parent / "2025 Parcel Layer.gdb"
    
    if not gdb_path.exists():
        print(f"Error: Geodatabase not found at {gdb_path}")
        print("Please ensure the '2025 Parcel Layer.gdb' folder is in the project root")
        sys.exit(1)
    
    process_geodatabase(str(gdb_path), batch_size=args.batch_size, limit=args.limit)
    print("\n" + "="*60)
    print("✅ Processing complete!")
    if args.limit:
        print(f"   Processed {args.limit:,} sample parcels")
        print("   To process all parcels, run without --limit flag")
    print("="*60)
