"""
Fix missing owners by matching CAMA_Link from geodatabase to Excel records
This is more reliable than address matching since addresses from reverse geocoding may not match Excel
"""
import sys
import os
from pathlib import Path
from typing import Dict, Optional
import pandas as pd
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from multiprocessing import Pool, cpu_count
import json

# Add backend directory to path
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from models import Property
from database import SessionLocal

load_dotenv()

MUNICIPALITY = "Torrington"
CLEANED_FILE = "/Users/jacobmermelstein/Desktop/CT Data/2025 Post Duplicate Clean/Torrington_CAMA_2025_CLEANED.xlsx"
RAW_CSV_FILE = "/Users/jacobmermelstein/Desktop/CT Data/2025 Parcel Collection/Torrington_CAMA_2025.csv"

def parse_cama_link(cama_link: str) -> Optional[str]:
    """
    Parse CAMA_Link to get parcel ID
    Format: 76570-125/002/003 -> 125/2/3
    """
    if not cama_link or cama_link == 'None':
        return None
    
    try:
        # Remove prefix (76570-)
        if '-' in cama_link:
            parcel_part = cama_link.split('-', 1)[1]
        else:
            parcel_part = cama_link
        
        # Normalize: 125/002/003 -> 125/2/3 (remove leading zeros)
        parts = parcel_part.split('/')
        normalized_parts = [str(int(p)) if p.isdigit() else p for p in parts]
        return '/'.join(normalized_parts)
    except Exception:
        return None

def load_excel_by_parcel_id() -> Dict[str, str]:
    """Load Excel data keyed by parcel ID"""
    print("Loading Excel data...")
    
    try:
        df = pd.read_excel(CLEANED_FILE, engine='openpyxl')
        if len(df) > 1:
            first_row = df.iloc[0].astype(str).str.lower()
            if 'owner' in str(df.iloc[0].get('Full Name', '')).lower():
                df = df.iloc[1:].reset_index(drop=True)
        
        parcel_owner_map = {}
        
        for idx, row in df.iterrows():
            # Try different column names for parcel ID
            parcel_id = None
            for col in ['Parcel ID', 'Parcel_ID', 'PID', 'ParcelID']:
                if col in row and pd.notna(row[col]):
                    parcel_id = str(row[col]).strip()
                    break
            
            owner = str(row.get('Full Name', '')).strip()
            
            if parcel_id and parcel_id != 'nan' and owner and owner != 'nan':
                # Normalize parcel ID (remove leading zeros)
                try:
                    parts = parcel_id.split('/')
                    normalized_parts = [str(int(p)) if p.isdigit() else p for p in parts]
                    normalized_parcel = '/'.join(normalized_parts)
                    parcel_owner_map[normalized_parcel] = owner
                except Exception:
                    parcel_owner_map[parcel_id] = owner
        
        print(f"  Loaded {len(parcel_owner_map):,} parcel-owner mappings")
        return parcel_owner_map
    except Exception as e:
        print(f"  ⚠️  Error loading Excel: {e}")
        return {}

def load_raw_csv_by_cama_link() -> Dict[str, str]:
    """Load raw CSV data keyed by CAMA Site Link"""
    print("Loading raw CSV data...")
    
    if not os.path.exists(RAW_CSV_FILE):
        print(f"  ⚠️  Raw CSV file not found: {RAW_CSV_FILE}")
        return {}
    
    try:
        df = pd.read_csv(RAW_CSV_FILE, low_memory=False)
        
        cama_owner_map = {}
        
        for idx, row in df.iterrows():
            cama_link = str(row.get('CAMA Site Link', '')).strip() if pd.notna(row.get('CAMA Site Link')) else None
            owner = str(row.get('Owner', '')).strip() if pd.notna(row.get('Owner')) else None
            
            if cama_link and cama_link != 'nan' and cama_link and owner and owner != 'nan' and owner:
                cama_owner_map[cama_link] = owner
        
        print(f"  Loaded {len(cama_owner_map):,} CAMA link-owner mappings")
        return cama_owner_map
    except Exception as e:
        print(f"  ⚠️  Error loading raw CSV: {e}")
        return {}

def fix_owners_by_cama_link(dry_run: bool = False):
    """Fix missing owners by matching CAMA_Link"""
    print("=" * 60)
    print("Fixing Missing Owners by CAMA_Link")
    print("=" * 60)
    
    if dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
    
    db = SessionLocal()
    try:
        # Get properties without owners that have CAMA_Link
        properties = db.query(Property).filter(
            Property.municipality.ilike(f"%{MUNICIPALITY}%"),
            (Property.owner_name.is_(None)) | (Property.owner_name == '') | (Property.owner_name == 'None'),
            Property.additional_data.isnot(None)
        ).all()
        
        print(f"\nFound {len(properties):,} properties without owners (with CAMA_Link)")
        
        if len(properties) == 0:
            print("\n✅ All properties have owners!")
            return
        
        # Load Excel and CSV data
        parcel_owner_map = load_excel_by_parcel_id()
        cama_owner_map = load_raw_csv_by_cama_link()
        
        # Match and update
        updated = 0
        not_found = 0
        
        print(f"\nMatching properties...")
        for prop in properties:
            owner = None
            
            # Get CAMA_Link from additional_data
            if prop.additional_data:
                cama_data = json.loads(prop.additional_data) if isinstance(prop.additional_data, str) else prop.additional_data
                cama_link = cama_data.get('cama_link', '')
                
                if cama_link:
                    # Strategy 1: Match by CAMA_Link directly in raw CSV
                    if cama_link in cama_owner_map:
                        owner = cama_owner_map[cama_link]
                    else:
                        # Strategy 2: Parse CAMA_Link to get parcel ID and match in Excel
                        parcel_id = parse_cama_link(cama_link)
                        if parcel_id:
                            # Try exact match
                            if parcel_id in parcel_owner_map:
                                owner = parcel_owner_map[parcel_id]
                            else:
                                # Try with prop's parcel_id
                                if prop.parcel_id and prop.parcel_id in parcel_owner_map:
                                    owner = parcel_owner_map[prop.parcel_id]
            
            if owner:
                if not dry_run:
                    prop.owner_name = owner
                    updated += 1
                else:
                    print(f"  Would update {prop.parcel_id}: {owner}")
                    updated += 1
            else:
                not_found += 1
        
        if not dry_run:
            db.commit()
        
        print(f"\n✅ Updated {updated:,} properties with owners")
        if not_found > 0:
            print(f"⚠️  {not_found:,} properties still missing owners")
        
    finally:
        db.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode')
    args = parser.parse_args()
    
    fix_owners_by_cama_link(dry_run=args.dry_run)
