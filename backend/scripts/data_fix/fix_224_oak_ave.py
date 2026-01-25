"""
Fix 224 Oak Ave owner information - should be "224 OAK AVE LLC" from Excel
"""
import sys
from pathlib import Path
import pandas as pd
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from models import Property
from database import SessionLocal
from scripts.data_import.import_bridgeport_cama_2025 import normalize_address, map_to_database_fields

def fix_224_oak_ave(dry_run: bool = False):
    """Fix owner for 224 Oak Ave"""
    
    # Get correct data from Excel
    cleaned_file = '/Users/jacobmermelstein/Desktop/CT Data/2025 Post Duplicate Clean/Torrington_CAMA_2025_CLEANED.xlsx'
    df = pd.read_excel(cleaned_file, engine='openpyxl')
    
    # Skip tracking row
    if len(df) > 1:
        first_row = df.iloc[0].astype(str).str.lower()
        if 'owner' in str(df.iloc[0].get('Full Name', '')).lower():
            df = df.iloc[1:].reset_index(drop=True)
    
    # Find 224 OAK AVE
    oak_row = df[df['Property Address'].str.contains('^224.*OAK AVE$', case=False, na=False, regex=True)]
    
    if len(oak_row) == 0:
        print("❌ 224 OAK AVE not found in Excel file")
        return
    
    row = oak_row.iloc[0]
    combined = row.to_dict()
    db_record = map_to_database_fields(combined)
    
    correct_owner = db_record.get('owner_name')
    correct_address = db_record.get('address')
    
    print(f"Correct data from Excel:")
    print(f"  Address: {correct_address}")
    print(f"  Owner: {correct_owner}")
    
    # Find property in database
    db = SessionLocal()
    try:
        prop = db.query(Property).filter(
            Property.municipality.ilike('%Torrington%'),
            Property.address.ilike('%224%OAK%')
        ).first()
        
        if not prop:
            print("❌ Property not found in database")
            return
        
        print(f"\nCurrent database entry:")
        print(f"  Parcel ID: {prop.parcel_id}")
        print(f"  Address: {prop.address}")
        print(f"  Owner: {prop.owner_name}")
        
        if prop.owner_name == correct_owner:
            print("\n✅ Owner is already correct!")
            return
        
        print(f"\n⚠️  Owner mismatch detected!")
        print(f"   Current: {prop.owner_name}")
        print(f"   Should be: {correct_owner}")
        
        if not dry_run:
            # Update owner
            prop.owner_name = correct_owner
            # Also update address if different
            if correct_address and prop.address != correct_address:
                prop.address = correct_address
                print(f"   Also updating address: {correct_address}")
            
            db.commit()
            print(f"\n✅ Updated property {prop.parcel_id} with correct owner: {correct_owner}")
        else:
            print(f"\n🔍 DRY RUN - Would update owner to: {correct_owner}")
    
    finally:
        db.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Fix 224 Oak Ave owner information')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode')
    args = parser.parse_args()
    
    fix_224_oak_ave(dry_run=args.dry_run)
