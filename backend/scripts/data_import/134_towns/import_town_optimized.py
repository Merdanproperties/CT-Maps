"""
Generic Optimized Import for Any Town - Uses Geodatabase Excel (No Geocoding!)
Reads geodatabase Excel (has geometry), cleaned Excel, and CSV
Matches all three and imports with bulk operations

Reference: See docs/IMPORT_TOWN_OPTIMIZED_REFERENCE.md in this folder
(backend/scripts/data_import/134_towns/) or Documentation/guides/ for
why this works and how to run it smoothly (no duplicates, parcel_id per-town, etc.).
"""
import sys
import os
import argparse
import json
from pathlib import Path
from datetime import date, datetime
from typing import Dict, List, Optional
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from geoalchemy2 import WKTElement
from shapely import wkt

# #region agent log
# Project root is 5 levels up (script in backend/scripts/data_import/134_towns/)
_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
DEBUG_LOG_PATH = _PROJECT_ROOT / ".cursor" / "debug.log"
def debug_log(location: str, message: str, data: dict, hypothesis_id: str = None):
    """Write debug log entry"""
    try:
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "location": location,
            "message": message,
            "data": data,
            "sessionId": "debug-session",
            "runId": "run1",
            "hypothesisId": hypothesis_id
        }
        with open(DEBUG_LOG_PATH, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
    except Exception:
        pass
# #endregion

# Backend is 4 levels up (script in backend/scripts/data_import/134_towns/)
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from models import Property, Base
from database import engine, SessionLocal

# Import reusable functions
from scripts.data_import.import_bridgeport_cama_2025 import (
    normalize_address,
    read_cleaned_excel,
    read_raw_csv,
    match_and_combine,
    map_to_database_fields,
)

# Default paths
DEFAULT_DATA_DIR = Path("/Users/jacobmermelstein/Desktop/CT Data")
GEO_EXCEL_DIR = _PROJECT_ROOT / "Analysis scripts" / "Excel geodatabase all towns"

def read_geodatabase_excel(excel_path: Path) -> pd.DataFrame:
    """Read geodatabase Excel file"""
    print(f"  Reading geodatabase Excel: {excel_path}")
    df = pd.read_excel(excel_path, engine='openpyxl')
    print(f"  ✅ Loaded {len(df):,} records")
    return df

def create_point_from_coords(lon: float, lat: float) -> WKTElement:
    """Create Point geometry from lat/lon"""
    wkt_string = f"POINT({lon} {lat})"
    return WKTElement(wkt_string, srid=4326)

def create_geometry_from_wkt(geometry_wkt: str) -> Optional[WKTElement]:
    """Create geometry from WKT string (supports POLYGON, MULTIPOLYGON, POINT)"""
    if not geometry_wkt or pd.isna(geometry_wkt):
        return None
    try:
        # Validate WKT format
        wkt.loads(str(geometry_wkt))
        return WKTElement(str(geometry_wkt), srid=4326)
    except Exception as e:
        return None

def normalize_municipality(municipality: str) -> str:
    """
    Normalize municipality name to standard Title Case, handling typos, invalid entries, and abbreviations.
    Returns standardized name from valid CT towns list if found, otherwise returns normalized version.
    """
    if not municipality or pd.isna(municipality):
        return municipality
    
    # Complete list of all 169 Connecticut towns (standardized names)
    ALL_169_CT_TOWNS = [
        "Andover", "Ansonia", "Ashford", "Avon", "Barkhamsted", "Beacon Falls",
        "Berlin", "Bethany", "Bethel", "Bethlehem", "Bloomfield", "Bolton",
        "Bozrah", "Branford", "Bridgeport", "Bridgewater", "Bristol", "Brookfield",
        "Brooklyn", "Burlington", "Canaan", "Canterbury", "Canton", "Chaplin",
        "Cheshire", "Chester", "Clinton", "Colchester", "Colebrook", "Columbia",
        "Cornwall", "Coventry", "Cromwell", "Danbury", "Darien", "Deep River",
        "Derby", "Durham", "East Granby", "East Haddam", "East Hampton", "East Hartford",
        "East Haven", "East Lyme", "East Windsor", "Eastford", "Easton", "Ellington",
        "Enfield", "Essex", "Fairfield", "Farmington", "Franklin", "Glastonbury",
        "Goshen", "Granby", "Greenwich", "Griswold", "Groton", "Guilford",
        "Haddam", "Hamden", "Hampton", "Hartford", "Hartland", "Harwinton",
        "Hebron", "Kent", "Killingly", "Killingworth", "Lebanon", "Ledyard",
        "Lisbon", "Litchfield", "Lyme", "Madison", "Manchester", "Mansfield",
        "Marlborough", "Meriden", "Middlebury", "Middlefield", "Middletown", "Milford",
        "Monroe", "Montville", "Morris", "Naugatuck", "New Britain", "New Canaan",
        "New Fairfield", "New Hartford", "New Haven", "New London", "New Milford",
        "Newington", "Newtown", "Norfolk", "North Branford", "North Canaan", "North Haven",
        "North Stonington", "Norwalk", "Norwich", "Old Lyme", "Old Saybrook", "Orange",
        "Oxford", "Plainfield", "Plainville", "Plymouth", "Pomfret", "Portland",
        "Preston", "Prospect", "Putnam", "Redding", "Ridgefield", "Rocky Hill",
        "Roxbury", "Salem", "Salisbury", "Scotland", "Seymour", "Sharon",
        "Shelton", "Sherman", "Simsbury", "Somers", "South Windsor", "Southbury",
        "Southington", "Sprague", "Stafford", "Stamford", "Sterling", "Stonington",
        "Stratford", "Suffield", "Thomaston", "Thompson", "Tolland", "Torrington",
        "Trumbull", "Union", "Vernon", "Voluntown", "Wallingford", "Warren",
        "Washington", "Waterbury", "Waterford", "Watertown", "West Hartford", "West Haven",
        "Westbrook", "Weston", "Westport", "Wethersfield", "Willington", "Wilton",
        "Winchester", "Windham", "Windsor", "Windsor Locks", "Wolcott", "Woodbridge",
        "Woodbury", "Woodstock"
    ]
    
    # Convert to string and clean
    name = str(municipality).strip()
    
    # Filter out obviously invalid entries
    # Handle "SheltonREVAL" -> "Shelton"
    if 'REVAL' in name:
        name = name.replace('REVAL', '').strip()
    
    # Skip invalid entries
    if 'STATIC' in name or 'DATA BASE' in name:
        return None  # Skip invalid entries like "STATIC DATA BASE"
    
    # Skip addresses (e.g., "200 PRATT ST")
    if 'PRATT ST' in name or (name.split() and name.split()[0].isdigit()):
        return None
    
    # Remove year suffix (e.g., "Farmington 2022" -> "Farmington")
    parts = name.split()
    if len(parts) > 1 and parts[-1].isdigit() and len(parts[-1]) == 4:
        name = ' '.join(parts[:-1])
    
    # Handle abbreviations
    abbreviation_map = {
        'e berlin': 'East Berlin',
        's glastonbury': 'Glastonbury',
        'n glastonbury': 'Glastonbury',
        'w glastonbury': 'Glastonbury',
    }
    
    name_lower = name.lower()
    if name_lower in abbreviation_map:
        return abbreviation_map[name_lower]
    
    # Common typo corrections (based on actual data)
    typo_corrections = {
        'kensjngton': 'Kensington',
        'sxouthington': 'Southington',
        'bristtol': 'Bristol',
        'wallinfdord': 'Wallingford',
        'milfrd': 'Milford',
        'woobridge': 'Woodbridge',
        'barkhamstead': 'Barkhamsted',
        'winsted': 'Winchester',
    }
    
    if name_lower in typo_corrections:
        return typo_corrections[name_lower]
    
    # Try exact match first (case-insensitive)
    for town in ALL_169_CT_TOWNS:
        if town.lower() == name_lower:
            return town
    
    # Try matching with normalized spacing (handle multiple spaces, etc.)
    normalized_input = ' '.join(name.split())
    normalized_input_lower = normalized_input.lower()
    for town in ALL_169_CT_TOWNS:
        if town.lower() == normalized_input_lower:
            return town
    
    # If no match found, return Title Case version (better than nothing)
    return normalized_input.title()

def _not_added_row(record: dict, municipality: str, reason: str) -> dict:
    """Build a flat row for the 'not added' Excel export (simple values only)."""
    address = record.get('Property Address') or record.get('address') or ''
    parcel_id = record.get('parcel_id') or record.get('geo_parcel_id')
    if not parcel_id and 'raw_Parcel ID' in record:
        parcel_id = record.get('raw_Parcel ID')
    return {
        'Municipality': municipality,
        'Parcel_ID': str(parcel_id).strip() if parcel_id is not None and pd.notna(parcel_id) else '',
        'Address': str(address).strip() if address else '',
        'Reason_Not_Added': reason,
        'Had_Geometry': record.get('has_geometry', False),
        'Geometry_Type': record.get('geometry_type') or '',
    }


def get_geodatabase_excel_path(municipality: str) -> Path:
    """Get geodatabase Excel path for a municipality"""
    # Try different naming conventions
    possible_names = [
        f"{municipality}.xlsx",
        f"{municipality.replace(' ', '_')}.xlsx",
        f"{municipality.upper()}.xlsx",
        f"{municipality.lower()}.xlsx",
        f"{municipality.replace(' ', '_').upper()}.xlsx",
    ]
    
    for name in possible_names:
        path = GEO_EXCEL_DIR / name
        if path.exists():
            return path
    
    # If not found, raise error
    raise FileNotFoundError(f"Geodatabase Excel not found for {municipality}. Tried: {possible_names}")

def import_town_optimized(
    municipality: str,
    geodatabase_excel_path: str = None,
    cleaned_excel_path: str = None,
    raw_csv_path: str = None,
    limit: Optional[int] = None,
    dry_run: bool = False
):
    """
    Optimized import: Uses geodatabase Excel (has geometry), cleaned Excel, and CSV
    No geocoding needed - geometry already in geodatabase Excel!
    """
    # Normalize municipality to Title Case for consistency
    normalized_municipality = normalize_municipality(municipality)
    if not normalized_municipality:
        raise ValueError(f"Invalid municipality name: '{municipality}' (normalized to None - likely invalid entry)")
    municipality = normalized_municipality
    
    print("=" * 80)
    print(f"OPTIMIZED IMPORT: {municipality.upper()}")
    print("=" * 80)
    print(f"Municipality: {municipality}")
    
    if dry_run:
        print("🔍 DRY RUN MODE - No database changes will be made")
    
    # Build file paths
    if not geodatabase_excel_path:
        geodatabase_excel_path = get_geodatabase_excel_path(municipality)
    if not cleaned_excel_path:
        cleaned_excel_path = DEFAULT_DATA_DIR / "2025 Post Duplicate Clean" / f"{municipality}_CAMA_2025_CLEANED.xlsx"
    if not raw_csv_path:
        raw_csv_path = DEFAULT_DATA_DIR / "2025 Parcel Collection" / f"{municipality}_CAMA_2025.csv"
    
    geodatabase_excel_path = Path(geodatabase_excel_path)
    cleaned_excel_path = Path(cleaned_excel_path)
    raw_csv_path = Path(raw_csv_path)
    
    print(f"\nGeodatabase Excel: {geodatabase_excel_path}")
    print(f"Cleaned Excel: {cleaned_excel_path}")
    print(f"Raw CSV: {raw_csv_path}")
    
    if not geodatabase_excel_path.exists():
        raise FileNotFoundError(f"Geodatabase Excel not found: {geodatabase_excel_path}")
    if not cleaned_excel_path.exists():
        raise FileNotFoundError(f"Cleaned Excel not found: {cleaned_excel_path}")
    if not raw_csv_path.exists():
        raise FileNotFoundError(f"Raw CSV not found: {raw_csv_path}")
    
    db = SessionLocal()
    try:
        # Step 1: Read geodatabase Excel (has geometry!)
        print("\n" + "=" * 80)
        print("STEP 1: Reading Geodatabase Excel (with geometry)")
        print("=" * 80)
        geo_df = read_geodatabase_excel(geodatabase_excel_path)
        geodatabase_total_count = len(geo_df)  # Track total geodatabase count
        if limit:
            geo_df = geo_df.head(limit)
            print(f"  ⚠️  Limited to first {limit:,} records for testing")
        
        # Create lookup by Parcel_ID and Location (NO CAMA_Link/Link - those don't exist in cleaned Excel/CSV)
        geo_lookup_by_parcel = {}
        geo_lookup_by_address = {}
        for idx, row in geo_df.iterrows():
            parcel_id = str(row.get('Parcel_ID', '')).strip() if pd.notna(row.get('Parcel_ID')) else None
            location = str(row.get('Location', '')).strip() if pd.notna(row.get('Location')) else None
            
            if parcel_id and parcel_id != 'nan':
                geo_lookup_by_parcel[parcel_id] = row.to_dict()
            if location:
                norm_addr = normalize_address(location)
                if norm_addr:
                    if norm_addr not in geo_lookup_by_address:
                        geo_lookup_by_address[norm_addr] = []
                    geo_lookup_by_address[norm_addr].append(row.to_dict())
        
        print(f"  ✅ Created lookups:")
        print(f"     - Parcel_ID: {len(geo_lookup_by_parcel):,}")
        print(f"     - Address: {len(geo_lookup_by_address):,}")
        
        # Step 2: Read cleaned Excel
        print("\n" + "=" * 80)
        print("STEP 2: Reading Cleaned Excel")
        print("=" * 80)
        cleaned_df = read_cleaned_excel(str(cleaned_excel_path), limit=limit)
        print(f"✅ Loaded {len(cleaned_df):,} records from cleaned Excel")
        
        # Step 3: Read raw CSV
        print("\n" + "=" * 80)
        print("STEP 3: Reading Raw CSV")
        print("=" * 80)
        raw_df, raw_lookup = read_raw_csv(str(raw_csv_path))
        print(f"✅ Loaded {len(raw_df):,} records from CSV")
        
        # Step 4: Match Excel + CSV
        print("\n" + "=" * 80)
        print("STEP 4: Matching Excel + CSV")
        print("=" * 80)
        combined_records = match_and_combine(cleaned_df, raw_lookup)
        print(f"✅ Combined {len(combined_records):,} records")
        
        # Step 5: Match with geodatabase Excel (add geometry)
        print("\n" + "=" * 80)
        print("STEP 5: Matching with Geodatabase Excel (adding geometry)")
        print("=" * 80)
        
        matched_count = 0
        unmatched_count = 0
        matched_by_parcel = 0
        matched_by_address = 0
        
        for record in combined_records:
            # Try to match by Parcel_ID first
            parcel_id = record.get('parcel_id')
            if not parcel_id and 'raw_Parcel ID' in record:
                parcel_id = str(record['raw_Parcel ID']).strip()
            
            geo_record = None
            if parcel_id and parcel_id in geo_lookup_by_parcel:
                geo_record = geo_lookup_by_parcel[parcel_id]
                matched_by_parcel += 1
            else:
                # Try to match by address
                address = record.get('Property Address', '')
                if address:
                    norm_addr = normalize_address(address)
                    if norm_addr in geo_lookup_by_address:
                        # Take first match
                        geo_record = geo_lookup_by_address[norm_addr][0]
                        matched_by_address += 1
            
            if geo_record:
                # Add geometry data to record - prefer full Geometry_WKT, fallback to lat/lon
                geometry_wkt = geo_record.get('Geometry_WKT')
                if pd.notna(geometry_wkt) and geometry_wkt:
                    record['geometry_wkt'] = str(geometry_wkt)
                    record['has_geometry'] = True
                    record['geometry_type'] = 'full'
                elif pd.notna(geo_record.get('Latitude')) and pd.notna(geo_record.get('Longitude')):
                    record['latitude'] = float(geo_record['Latitude'])
                    record['longitude'] = float(geo_record['Longitude'])
                    record['has_geometry'] = True
                    record['geometry_type'] = 'point'
                else:
                    record['has_geometry'] = False
                    record['geometry_type'] = None
                record['geo_parcel_id'] = geo_record.get('Parcel_ID')
                matched_count += 1
            else:
                record['has_geometry'] = False
                record['geometry_type'] = None
                unmatched_count += 1
        
        print(f"✅ Matched: {matched_count:,} | ❌ Unmatched: {unmatched_count:,}")
        print(f"   Match breakdown:")
        print(f"     - By Parcel_ID: {matched_by_parcel:,}")
        print(f"     - By Address: {matched_by_address:,}")
        
        # Step 6: Import to database with bulk operations
        print("\n" + "=" * 80)
        print("STEP 6: Importing to Database (Bulk Operations)")
        print("=" * 80)
        
        # Ensure PostGIS extension
        Base.metadata.create_all(bind=engine)
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
            conn.commit()
        
        # Get existing properties
        existing_parcels = set()
        initial_count = db.query(Property).filter(func.lower(Property.municipality) == municipality.lower()).count()
        # #region agent log
        debug_log("import_town_optimized.py:354", "Initial count before processing", {
            "municipality": municipality,
            "initial_count": initial_count
        }, "H1")
        # #endregion
        for prop in db.query(Property.parcel_id).filter(func.lower(Property.municipality) == municipality.lower()).all():
            if prop.parcel_id:
                existing_parcels.add(str(prop.parcel_id).strip())
        print(f"  Found {len(existing_parcels):,} existing properties in database")
        
        # Prepare bulk insert/update data
        properties_to_insert = []
        properties_to_update = []
        seen_parcel_ids = set()  # Track parcel_ids in this batch to avoid duplicates
        not_added_records = []  # Records skipped or failed (exported to Excel per town)
        
        for i, record in enumerate(combined_records, 1):
            try:
                # Skip if no geometry
                if not record.get('has_geometry'):
                    not_added_records.append(_not_added_row(record, municipality, 'No geometry (unmatched with geodatabase)'))
                    continue
                
                # Map to database fields
                db_record = map_to_database_fields(record)
                
                # Remove municipality from db_record to prevent override (we use normalized parameter instead)
                db_record.pop('municipality', None)
                
                # Get parcel_id
                parcel_id = record.get('parcel_id') or record.get('geo_parcel_id')
                if not parcel_id and 'raw_Parcel ID' in record:
                    parcel_id = str(record['raw_Parcel ID']).strip()
                
                if not parcel_id or parcel_id == 'nan':
                    parcel_id = f"{municipality}_{i}_{hash(db_record.get('address', ''))}"
                
                # Normalize parcel_id
                parcel_id = str(parcel_id).strip()
                
                # Skip if we've already processed this parcel_id in this batch
                if parcel_id in seen_parcel_ids:
                    not_added_records.append(_not_added_row(record, municipality, 'Duplicate parcel_id in batch'))
                    continue
                seen_parcel_ids.add(parcel_id)
                
                # Create geometry - prefer full polygon, fallback to Point
                geometry_wkt = None
                if record.get('geometry_type') == 'full' and record.get('geometry_wkt'):
                    # Use full polygon geometry from Geometry_WKT
                    geometry_wkt = create_geometry_from_wkt(record['geometry_wkt'])
                elif record.get('geometry_type') == 'point':
                    # Fallback to Point geometry from lat/lon
                    lon = record.get('longitude')
                    lat = record.get('latitude')
                    if lon and lat:
                        geometry_wkt = create_point_from_coords(lon, lat)
                
                if not geometry_wkt:
                    not_added_records.append(_not_added_row(record, municipality, 'Invalid or missing geometry (WKT/lat-lon)'))
                    continue
                
                # Check if exists in database
                if parcel_id in existing_parcels:
                    # Will update - only include fields that have values (don't overwrite with NULL)
                    # CRITICAL: Filter by BOTH parcel_id AND municipality since parcel_id is only unique per town
                    existing = db.query(Property).filter(
                        Property.parcel_id == parcel_id,
                        func.lower(Property.municipality) == municipality.lower()
                    ).first()
                    if existing:
                        old_municipality = existing.municipality
                        # CRITICAL FIX: Don't update if municipality differs - this would move properties between towns!
                        if old_municipality and old_municipality.lower() != municipality.lower():
                            # #region agent log
                            debug_log("import_town_optimized.py:410", "Skipping update - parcel_id exists with different municipality", {
                                "municipality": municipality,
                                "parcel_id": parcel_id,
                                "old_municipality": old_municipality,
                                "new_municipality": municipality,
                                "action": "SKIPPED"
                            }, "H3")
                            # #endregion
                            not_added_records.append(_not_added_row(record, municipality, f'Parcel exists in different municipality ({old_municipality})'))
                            continue  # Skip - don't move property between towns
                        # Only update fields that have non-NULL values to avoid overwriting existing data
                        update_data = {
                            'id': existing.id,
                            'municipality': municipality,  # Always use normalized municipality
                            'geometry': geometry_wkt
                        }
                        # Only add fields from db_record that have values (not None/empty)
                        for k, v in db_record.items():
                            if k != 'parcel_id' and v is not None:
                                # For strings, also check if not empty
                                if isinstance(v, str) and v.strip():
                                    update_data[k] = v
                                elif not isinstance(v, str):
                                    update_data[k] = v
                        # #region agent log
                        if old_municipality != municipality:
                            debug_log("import_town_optimized.py:430", "Municipality change detected in update (same town, different casing)", {
                                "municipality": municipality,
                                "parcel_id": parcel_id,
                                "old_municipality": old_municipality,
                                "new_municipality": municipality
                            }, "H3")
                        # #endregion
                        properties_to_update.append(update_data)
                else:
                    # Will insert
                    property_data = {
                        'parcel_id': parcel_id,
                        'geometry': geometry_wkt,
                        'municipality': municipality,  # Always use normalized municipality
                        'data_source': f'{municipality} CAMA 2025 (Geodatabase Excel)',
                        'last_updated': date.today(),
                        **db_record  # db_record no longer contains municipality (removed above)
                    }
                    properties_to_insert.append(property_data)
                    existing_parcels.add(parcel_id)  # Track to avoid duplicates in future batches
                
                if i % 1000 == 0:
                    print(f"  Processed: {i:,}/{len(combined_records):,} | "
                          f"To insert: {len(properties_to_insert):,} | "
                          f"To update: {len(properties_to_update):,}")
            
            except Exception as e:
                if i <= 10:
                    print(f"  ⚠️  Error processing record {i}: {e}")
                not_added_records.append(_not_added_row(record, municipality, f'Error: {e}'))
                continue
        
        # Bulk insert
        if not dry_run and properties_to_insert:
            print(f"\n  Inserting {len(properties_to_insert):,} properties...")
            BATCH_SIZE = 1000
            inserted = 0
            for i in range(0, len(properties_to_insert), BATCH_SIZE):
                batch = properties_to_insert[i:i+BATCH_SIZE]
                count_before = db.query(Property).filter(func.lower(Property.municipality) == municipality.lower()).count()
                # #region agent log
                debug_log("import_town_optimized.py:457", "Before bulk insert batch", {
                    "municipality": municipality,
                    "batch_num": i//BATCH_SIZE + 1,
                    "batch_size": len(batch),
                    "count_before": count_before
                }, "H1")
                # #endregion
                try:
                    db.bulk_insert_mappings(Property, batch)
                    db.commit()
                    inserted += len(batch)
                    count_after = db.query(Property).filter(func.lower(Property.municipality) == municipality.lower()).count()
                    # #region agent log
                    debug_log("import_town_optimized.py:465", "After bulk insert batch commit", {
                        "municipality": municipality,
                        "batch_num": i//BATCH_SIZE + 1,
                        "count_before": count_before,
                        "count_after": count_after,
                        "expected_increase": len(batch),
                        "actual_increase": count_after - count_before
                    }, "H1")
                    # #endregion
                    print(f"  ✅ Inserted batch {i//BATCH_SIZE + 1}: {len(batch):,} (Total: {inserted:,})")
                except Exception as e:
                    db.rollback()
                    # #region agent log
                    debug_log("import_town_optimized.py:475", "Bulk insert failed, rolling back", {
                        "municipality": municipality,
                        "batch_num": i//BATCH_SIZE + 1,
                        "error": str(e),
                        "count_before_rollback": count_before
                    }, "H2")
                    # #endregion
                    # Fall back to individual inserts with duplicate handling
                    print(f"  ⚠️  Batch insert failed, using individual inserts for batch {i//BATCH_SIZE + 1}...")
                    for prop_data in batch:
                        try:
                            # Check if parcel_id exists GLOBALLY (database has global unique constraint on parcel_id)
                            # Even though parcel_id should be unique per town, the DB constraint is global
                            existing_global = db.query(Property).filter(
                                Property.parcel_id == prop_data['parcel_id']
                            ).first()
                            
                            if existing_global:
                                # Check if it's in the same municipality
                                if existing_global.municipality and existing_global.municipality.lower() == municipality.lower():
                                    # Same municipality - update it
                                    # #region agent log
                                    debug_log("import_town_optimized.py:487", "Duplicate parcel_id found in same municipality - updating", {
                                        "municipality": municipality,
                                        "parcel_id": prop_data.get('parcel_id'),
                                        "existing_municipality": existing_global.municipality
                                    }, "H4")
                                    # #endregion
                                    for key, value in prop_data.items():
                                        if key != 'parcel_id':
                                            setattr(existing_global, key, value)
                                    # Don't increment inserted since we're updating, not inserting
                                else:
                                    # Different municipality - skip it (parcel_id conflict)
                                    # #region agent log
                                    debug_log("import_town_optimized.py:495", "Skipping parcel_id that exists in different municipality", {
                                        "municipality": municipality,
                                        "parcel_id": prop_data.get('parcel_id'),
                                        "existing_municipality": existing_global.municipality,
                                        "new_municipality": municipality,
                                        "action": "SKIPPED"
                                    }, "H4")
                                    # #endregion
                                    continue  # Skip - parcel_id already exists in different town
                            else:
                                # No existing property - safe to insert
                                prop = Property(**prop_data)
                                db.add(prop)
                                inserted += 1
                        except Exception as ex:
                            # Catch any other errors (including IntegrityError if duplicate check missed something)
                            error_str = str(ex).lower()
                            if 'duplicate' in error_str or 'unique' in error_str or 'already exists' in error_str:
                                # It's a duplicate - skip it
                                if inserted < 10:  # Only show first few
                                    print(f"    ⚠️  Skipped duplicate: {prop_data.get('parcel_id', 'unknown')}")
                            else:
                                # Some other error
                                if inserted < 10:
                                    print(f"    ⚠️  Error inserting {prop_data.get('parcel_id', 'unknown')}: {ex}")
                            # #region agent log
                            debug_log("import_town_optimized.py:502", "Individual insert error", {
                                "municipality": municipality,
                                "parcel_id": prop_data.get('parcel_id'),
                                "error": str(ex)
                            }, "H4")
                            # #endregion
                    db.commit()
                    count_after_individual = db.query(Property).filter(func.lower(Property.municipality) == municipality.lower()).count()
                    # #region agent log
                    debug_log("import_town_optimized.py:510", "After individual inserts commit", {
                        "municipality": municipality,
                        "batch_num": i//BATCH_SIZE + 1,
                        "count_before": count_before,
                        "count_after": count_after_individual,
                        "inserted_count": inserted
                    }, "H1")
                    # #endregion
        
        # Bulk update
        if not dry_run and properties_to_update:
            print(f"\n  Updating {len(properties_to_update):,} properties...")
            BATCH_SIZE = 5000
            updated = 0
            for i in range(0, len(properties_to_update), BATCH_SIZE):
                batch = properties_to_update[i:i+BATCH_SIZE]
                count_before_update = db.query(Property).filter(func.lower(Property.municipality) == municipality.lower()).count()
                # Check municipality changes in batch
                municipality_changes = []
                for update_item in batch[:5]:  # Sample first 5
                    existing_prop = db.query(Property).filter(Property.id == update_item['id']).first()
                    if existing_prop:
                        old_muni = existing_prop.municipality
                        new_muni = update_item.get('municipality')
                        if old_muni != new_muni:
                            municipality_changes.append({"id": update_item['id'], "old": old_muni, "new": new_muni})
                # #region agent log
                debug_log("import_town_optimized.py:520", "Before bulk update batch", {
                    "municipality": municipality,
                    "batch_num": i//BATCH_SIZE + 1,
                    "batch_size": len(batch),
                    "count_before": count_before_update,
                    "municipality_changes_sample": municipality_changes
                }, "H2")
                # #endregion
                try:
                    db.bulk_update_mappings(Property, batch)
                    db.commit()
                    updated += len(batch)
                    count_after_update = db.query(Property).filter(func.lower(Property.municipality) == municipality.lower()).count()
                    # #region agent log
                    debug_log("import_town_optimized.py:532", "After bulk update batch commit", {
                        "municipality": municipality,
                        "batch_num": i//BATCH_SIZE + 1,
                        "count_before": count_before_update,
                        "count_after": count_after_update,
                        "count_change": count_after_update - count_before_update
                    }, "H2")
                    # #endregion
                    print(f"  ✅ Updated batch {i//BATCH_SIZE + 1}: {len(batch):,} (Total: {updated:,})")
                except Exception as e:
                    db.rollback()
                    count_after_rollback = db.query(Property).filter(func.lower(Property.municipality) == municipality.lower()).count()
                    # #region agent log
                    debug_log("import_town_optimized.py:543", "Bulk update failed, rolled back", {
                        "municipality": municipality,
                        "batch_num": i//BATCH_SIZE + 1,
                        "error": str(e),
                        "count_before": count_before_update,
                        "count_after_rollback": count_after_rollback
                    }, "H2")
                    # #endregion
                    print(f"  ⚠️  Error updating batch: {e}")
        
        # Get final count in database (for both dry_run and actual import)
        if not dry_run:
            final_db_count = db.query(Property).filter(func.lower(Property.municipality) == municipality.lower()).count()
            # #region agent log
            debug_log("import_town_optimized.py:502", "Final count after all operations", {
                "municipality": municipality,
                "initial_count": initial_count,
                "final_count": final_db_count,
                "inserted": len(properties_to_insert),
                "updated": len(properties_to_update),
                "expected_final": initial_count + len(properties_to_insert),
                "count_change": final_db_count - initial_count
            }, "H1")
            # #endregion
        else:
            final_db_count = len(properties_to_insert) + len(properties_to_update)  # Estimate for dry run
        
        total_imported = len(properties_to_insert) + len(properties_to_update)
        
        if dry_run:
            print(f"\n🔍 DRY RUN - Would insert: {len(properties_to_insert):,}, update: {len(properties_to_update):,}")
        else:
            print(f"\n✅ Import complete:")
            print(f"   Inserted: {len(properties_to_insert):,}")
            print(f"   Updated: {len(properties_to_update):,}")
            print(f"   Matched with geometry: {matched_count:,}")
            print(f"   Unmatched (no geometry): {unmatched_count:,}")
        
        # Export "not added" records to Excel per town
        _OUTPUT_DIR = Path(__file__).parent / "logs"
        _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        if not_added_records:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            out_path = _OUTPUT_DIR / f"{municipality.replace(' ', '_')}_Not_Added_{ts}.xlsx"
            df_not_added = pd.DataFrame(not_added_records)
            df_not_added.to_excel(out_path, index=False, engine="openpyxl")
            print(f"\n📋 Not-added export: {len(not_added_records):,} records → {out_path}")
        else:
            print(f"\n📋 No not-added records to export for {municipality}.")
        
        # Compare with geodatabase count
        print("\n" + "=" * 80)
        print("IMPORT SUMMARY & COUNT COMPARISON")
        print("=" * 80)
        print(f"Geodatabase Excel total: {geodatabase_total_count:,}")
        print(f"Final database count: {final_db_count:,}")
        print(f"This import (inserted + updated): {total_imported:,}")
        print(f"Matched with geometry: {matched_count:,}")
        print(f"Unmatched (no geometry): {unmatched_count:,}")
        
        # Calculate discrepancy
        discrepancy = geodatabase_total_count - final_db_count
        discrepancy_pct = (discrepancy / geodatabase_total_count * 100) if geodatabase_total_count > 0 else 0
        
        print(f"\n📊 Count Analysis:")
        print(f"   Discrepancy: {discrepancy:,} ({discrepancy_pct:.1f}%)")
        
        # Flag if significant discrepancy (>10%)
        if abs(discrepancy_pct) > 10:
            print(f"\n⚠️  WARNING: Significant discrepancy detected!")
            print(f"   This town may need the lat/lon import process instead.")
            print(f"   Consider using import_middletown_simplified.py approach.")
        elif abs(discrepancy_pct) > 5:
            print(f"\n⚠️  NOTE: Moderate discrepancy detected ({discrepancy_pct:.1f}%)")
            print(f"   Some records may not have matched between sources.")
        else:
            print(f"\n✅ Counts are close - import looks good!")
        
        sys.stdout.flush()  # So batch script log shows full summary before next step
        return {
            'inserted': len(properties_to_insert),
            'updated': len(properties_to_update),
            'matched': matched_count,
            'unmatched': unmatched_count,
            'not_added_count': len(not_added_records),
            'geodatabase_count': geodatabase_total_count,
            'final_db_count': final_db_count,
            'discrepancy_pct': discrepancy_pct
        }
    
    except Exception as e:
        print(f"\n❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Optimized town import using geodatabase Excel')
    parser.add_argument('municipality', type=str, help='Town name to import')
    parser.add_argument('--limit', type=int, help='Limit number of records (for testing)')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode (no database changes)')
    parser.add_argument('--geodatabase-excel', type=str, help='Path to geodatabase Excel file')
    parser.add_argument('--cleaned-excel', type=str, help='Path to cleaned Excel file')
    parser.add_argument('--csv', type=str, help='Path to raw CSV file')
    
    args = parser.parse_args()
    
    try:
        import_town_optimized(
            municipality=args.municipality,
            geodatabase_excel_path=args.geodatabase_excel,
            cleaned_excel_path=args.cleaned_excel,
            raw_csv_path=args.csv,
            limit=args.limit,
            dry_run=args.dry_run
        )
    except Exception as e:
        print(f"\n❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
