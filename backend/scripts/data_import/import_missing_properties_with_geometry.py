"""
Import missing properties with geometry from matched geodatabase parcels
Combines CAMA data from Excel with geometry from geodatabase
"""
import sys
from pathlib import Path
from typing import Dict, List, Optional
from datetime import date
import json
from shapely import wkt
from shapely.geometry import shape
from geoalchemy2 import WKTElement

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from models import Property
from database import SessionLocal
from scripts.data_import.import_bridgeport_cama_2025 import map_to_database_fields

MUNICIPALITY = "Torrington"

def convert_geometry_to_wkt(geometry_obj, source_crs='EPSG:6434') -> Optional[str]:
    """Convert geometry to WGS84 WKT for PostGIS"""
    try:
        if geometry_obj is None:
            return None
        
        # If it's already a string (WKT), parse it first
        if isinstance(geometry_obj, str):
            geom = wkt.loads(geometry_obj)
        else:
            geom = geometry_obj
        
        # Convert to WGS84 using GeoPandas
        from geopandas import GeoSeries
        geom_series = GeoSeries([geom], crs=source_crs)
        geom_wgs84 = geom_series.to_crs('EPSG:4326').iloc[0]
        
        # Ensure 2D geometry
        geom_2d = wkt.loads(wkt.dumps(geom_wgs84, output_dimension=2))
        
        # Convert to WKT
        return geom_2d.wkt
    except Exception as e:
        print(f"      ⚠️  Geometry conversion error: {e}")
        return None

def import_properties_with_geometry(
    matched_records: List[Dict],
    dry_run: bool = False
) -> Dict:
    """
    Import properties with geometry from matched geodatabase parcels
    """
    print("\n" + "=" * 60)
    print("Importing Missing Properties with Geometry")
    print("=" * 60)
    
    if dry_run:
        print("🔍 DRY RUN MODE - No database changes will be made")
    
    db = SessionLocal()
    
    try:
        # Get existing parcel IDs to check for updates vs new imports
        print("\nStep 1: Checking existing properties...")
        existing_parcels = {}
        for prop in db.query(Property).filter(
            Property.municipality.ilike(f"%{MUNICIPALITY}%")
        ).all():
            if prop.parcel_id:
                existing_parcels[str(prop.parcel_id).strip()] = prop
        
        print(f"  Found {len(existing_parcels):,} existing properties")
        
        # Separate records into new vs updates
        new_records = []
        update_records = []
        for record in matched_records:
            parcel_id = record.get('matched_parcel_id')
            if not parcel_id or str(parcel_id).strip() == '':
                # Generate unique parcel_id for empty ones
                excel_pid = record.get('parcel_id') or record.get('record', {}).get('parcel_id')
                if excel_pid and str(excel_pid).strip():
                    parcel_id = f"EXCEL-{str(excel_pid).strip()}"
                else:
                    address = record.get('address', '')
                    if address:
                        parcel_id = f"EXCEL-ADDR-{hash(address) % 1000000}"
                    else:
                        continue
            
            parcel_id = str(parcel_id).strip()
            if parcel_id in existing_parcels:
                # Update existing property
                record['existing_property'] = existing_parcels[parcel_id]
                update_records.append(record)
            else:
                # New property
                new_records.append(record)
        
        print(f"\nStep 2: Categorizing records...")
        print(f"  Total matched records: {len(matched_records):,}")
        print(f"  New properties to import: {len(new_records):,}")
        print(f"  Existing properties to update: {len(update_records):,}")
        
        if not new_records and not update_records:
            print("\n✅ All matched properties already in database!")
            return {'imported': 0, 'updated': 0, 'errors': 0, 'skipped': len(matched_records)}
        
        # Update existing properties first
        updated_count = 0
        errors = 0
        if update_records:
            print(f"\nStep 3: Updating {len(update_records):,} existing properties...")
            for i, record in enumerate(update_records, 1):
                try:
                    prop = record['existing_property']
                    excel_record = record.get('record', {})
                    db_record = map_to_database_fields(excel_record)
                    
                    # Update address if missing or incomplete
                    new_address = db_record.get('address') or record.get('address', '')
                    if new_address and (not prop.address or prop.address.strip() == '' or 'MARGERIE ST' in prop.address.upper() and '12' not in prop.address):
                        if not dry_run:
                            prop.address = new_address
                    
                    # Update CAMA data if missing
                    if not prop.owner_name and db_record.get('owner_name'):
                        if not dry_run:
                            prop.owner_name = db_record['owner_name']
                    if not prop.assessed_value and db_record.get('assessed_value'):
                        if not dry_run:
                            prop.assessed_value = db_record['assessed_value']
                    # Add other CAMA fields as needed
                    
                    updated_count += 1
                    if i % 10 == 0:
                        print(f"  Progress: {i:,}/{len(update_records):,} updated...")
                except Exception as e:
                    if errors <= 10:
                        print(f"      ⚠️  Error updating {record.get('address', 'unknown')}: {e}")
                    errors += 1
                    if not dry_run:
                        db.rollback()
                    continue
        
        # Import new properties
        print(f"\nStep 4: Importing {len(new_records):,} new properties...")
        imported = 0
        skipped = 0
        
        for i, record in enumerate(new_records, 1):
            try:
                # Get CAMA data from Excel record
                excel_record = record.get('record', {})
                db_record = map_to_database_fields(excel_record)
                
                # Get geometry from matched geodatabase parcel (already in WGS84 WKT)
                geometry_wkt = record.get('matched_geometry_wkt')
                if not geometry_wkt:
                    skipped += 1
                    continue
                
                # Validate WKT (should already be in WGS84)
                try:
                    from shapely import wkt
                    geom = wkt.loads(geometry_wkt)
                    # Ensure 2D
                    geom_2d = wkt.loads(wkt.dumps(geom, output_dimension=2))
                    geometry_wkt_valid = geom_2d.wkt
                except Exception as e:
                    print(f"      ⚠️  WKT validation error: {e}")
                    skipped += 1
                    continue
                
                # Use parcel_id from geodatabase (not PID from CSV)
                parcel_id = record.get('matched_parcel_id')
                if not parcel_id or str(parcel_id).strip() == '':
                    # Generate unique parcel_id from Excel PID or address
                    excel_pid = record.get('parcel_id') or record.get('record', {}).get('parcel_id')
                    if excel_pid and str(excel_pid).strip():
                        parcel_id = f"EXCEL-{str(excel_pid).strip()}"
                    else:
                        # Use address-based ID as last resort
                        address = record.get('address', '')
                        if address:
                            parcel_id = f"EXCEL-ADDR-{hash(address) % 1000000}"
                        else:
                            skipped += 1
                            continue
                else:
                    parcel_id = str(parcel_id).strip()
                
                # Create property record
                property_data = {
                    'parcel_id': str(parcel_id).strip(),
                    'address': db_record.get('address') or record.get('address', ''),
                    'city': MUNICIPALITY,
                    'municipality': MUNICIPALITY,
                    'zip_code': db_record.get('zip_code'),
                    'owner_name': db_record.get('owner_name'),
                    'owner_address': db_record.get('owner_address'),
                    'owner_city': db_record.get('owner_city'),
                    'owner_state': db_record.get('owner_state', 'CT'),
                    'owner_zip': db_record.get('owner_zip'),
                    'owner_phone': db_record.get('owner_phone'),
                    'owner_email': db_record.get('owner_email'),
                    'assessed_value': db_record.get('assessed_value'),
                    'land_value': db_record.get('land_value'),
                    'building_value': db_record.get('building_value'),
                    'total_value': db_record.get('total_value'),
                    'property_type': db_record.get('property_type'),
                    'land_use': db_record.get('land_use'),
                    'lot_size_sqft': db_record.get('lot_size_sqft'),
                    'building_area_sqft': db_record.get('building_area_sqft'),
                    'year_built': db_record.get('year_built'),
                    'bedrooms': db_record.get('bedrooms'),
                    'bathrooms': db_record.get('bathrooms'),
                    'stories': db_record.get('stories'),
                    'total_rooms': db_record.get('total_rooms'),
                    'last_sale_price': db_record.get('last_sale_price'),
                    'last_sale_date': db_record.get('last_sale_date'),
                    'is_absentee': db_record.get('is_absentee', 0),
                    'data_source': 'CAMA + Geodatabase (Spatial Match)',
                    'last_updated': date.today(),
                    'geometry': WKTElement(geometry_wkt_valid, srid=4326)
                }
                
                # Create property
                if not dry_run:
                    prop = Property(**property_data)
                    db.add(prop)
                    
                    # Commit periodically
                    if i % 100 == 0:
                        db.commit()
                        print(f"  Progress: {i:,}/{len(new_records):,} | Imported: {imported:,} | Errors: {errors:,}")
                
                imported += 1
                
            except Exception as e:
                errors += 1
                if errors <= 10:
                    print(f"      ⚠️  Error importing {record.get('address', 'unknown')}: {e}")
                if not dry_run:
                    db.rollback()
                continue
        
        # Final commit
        if not dry_run and (imported > 0 or updated_count > 0):
            db.commit()
            print(f"\n✅ Committed {imported:,} new properties and {updated_count:,} updates to database")
        elif dry_run:
            print(f"\n  🔍 DRY RUN: Would import {imported:,} properties and update {updated_count:,}")
        
        print(f"\n📊 Import Summary:")
        print(f"  ✅ Imported: {imported:,}")
        print(f"  🔄 Updated: {updated_count:,}")
        print(f"  ❌ Errors: {errors:,}")
        print(f"  ⏭️  Skipped: {skipped:,}")
        
        return {
            'imported': imported,
            'updated': updated_count,
            'errors': errors,
            'skipped': skipped
        }
        
    finally:
        db.close()

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Import missing properties with geometry')
    parser.add_argument('--dry-run', action='store_true', help='Run without making database changes')
    args = parser.parse_args()
    
    # Load matched records
    matched_file = "logs/matched_to_geodatabase.json"
    try:
        with open(matched_file, 'r') as f:
            matched_records = json.load(f)
        print(f"Loaded {len(matched_records):,} matched records from {matched_file}")
    except FileNotFoundError:
        print(f"⚠️  Matched records file not found: {matched_file}")
        print("   Run match_to_geodatabase_spatially.py first")
        return
    
    # Import properties
    result = import_properties_with_geometry(matched_records, dry_run=args.dry_run)
    
    return result

if __name__ == "__main__":
    result = main()
    print("\n✅ Import complete!")
