"""
Fix all missing owner information by matching properties to Excel files
Uses address-based matching to find owners from CAMA data
"""
import sys
import os
from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from multiprocessing import Pool, cpu_count

# Add backend directory to path
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from models import Property
from database import SessionLocal
from scripts.data_import.import_bridgeport_cama_2025 import normalize_address

load_dotenv()

def load_excel_owners(municipality: str) -> Dict[str, str]:
    """Load owners from Excel file, keyed by normalized address"""
    excel_file = f'/Users/jacobmermelstein/Desktop/CT Data/2025 Post Duplicate Clean/{municipality}_CAMA_2025_CLEANED.xlsx'
    
    if not os.path.exists(excel_file):
        return {}
    
    try:
        df = pd.read_excel(excel_file, engine='openpyxl')
        if len(df) > 1:
            first_row = df.iloc[0].astype(str).str.lower()
            if 'owner' in str(df.iloc[0].get('Full Name', '')).lower():
                df = df.iloc[1:].reset_index(drop=True)
        
        owner_map = {}
        duplicate_addresses = set()
        
        for idx, row in df.iterrows():
            addr = row.get('Property Address', '')
            owner = row.get('Full Name', '')
            
            if pd.notna(addr) and addr and pd.notna(owner) and owner:
                normalized = normalize_address(str(addr))
                if normalized:
                    owner_str = str(owner).strip()
                    if normalized in owner_map:
                        # Duplicate address - mark it
                        duplicate_addresses.add(normalized)
                        # Keep first occurrence
                        continue
                    owner_map[normalized] = owner_str
        
        print(f"  Loaded {len(owner_map):,} unique addresses with owners")
        if duplicate_addresses:
            print(f"  Found {len(duplicate_addresses):,} addresses with duplicates (using first match)")
        
        return owner_map
    except Exception as e:
        print(f"  ⚠️  Error loading Excel for {municipality}: {e}")
        return {}

def process_property_batch(args: tuple) -> List[tuple]:
    """Process a batch of properties to get owners"""
    property_ids, municipality, excel_owners = args
    
    results = []
    db = SessionLocal()
    
    try:
        for prop_id in property_ids:
            prop = db.query(Property).filter(Property.id == prop_id).first()
            if not prop:
                results.append((prop_id, None))
                continue
            
            # Skip if already has owner
            if prop.owner_name and prop.owner_name != 'None' and prop.owner_name.strip():
                results.append((prop_id, prop.owner_name))
                continue
            
            owner = None
            
            # Match by address - try multiple strategies
            if prop.address:
                norm_addr = normalize_address(prop.address)
                
                # Strategy 1: Exact normalized match
                if norm_addr and norm_addr in excel_owners:
                    owner = excel_owners[norm_addr]
                else:
                    # Strategy 2: Partial match (try without house number)
                    if norm_addr:
                        parts = norm_addr.split(' ', 1)
                        if len(parts) == 2:
                            street_only = parts[1]  # Just the street name
                            # Find any address that ends with this street
                            for excel_norm, excel_owner in excel_owners.items():
                                if excel_norm.endswith(' ' + street_only) or excel_norm == street_only:
                                    owner = excel_owner
                                    break
            
            results.append((prop_id, owner))
            
    finally:
        db.close()
    
    return results

def fix_missing_owners(municipality: str = None, dry_run: bool = False):
    """Fix all missing owners"""
    print("=" * 60)
    print("Fixing Missing Owner Information")
    print("=" * 60)
    
    if dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
    
    db = SessionLocal()
    try:
        # Get properties without owners
        query = db.query(Property).filter(
            (Property.owner_name.is_(None)) | 
            (Property.owner_name == '') | 
            (Property.owner_name == 'None')
        )
        
        if municipality:
            query = query.filter(Property.municipality.ilike(f'%{municipality}%'))
        
        properties = query.all()
        
        print(f"\nFound {len(properties):,} properties without owners")
        
        if len(properties) == 0:
            print("\n✅ All properties have owners!")
            return
        
        # Load Excel owners for matching
        municipalities = set()
        for prop in properties:
            municipalities.add(prop.municipality or '')
        
        excel_owners = {}
        for mun in municipalities:
            if mun:
                print(f"\nLoading Excel owners for {mun}...")
                mun_owners = load_excel_owners(mun)
                excel_owners.update(mun_owners)
        
        print(f"\nTotal Excel owners loaded: {len(excel_owners):,}")
        
        # Process in parallel batches
        property_ids = [p.id for p in properties]
        num_workers = cpu_count()
        chunk_size = max(500, len(property_ids) // num_workers)
        chunks = [property_ids[i:i+chunk_size] for i in range(0, len(property_ids), chunk_size)]
        
        print(f"\nProcessing {len(chunks)} batches with {num_workers} workers...")
        
        all_results = []
        completed = 0
        with Pool(num_workers) as pool:
            chunk_args = [(chunk, municipality, excel_owners) for chunk in chunks]
            batch_results = pool.imap(process_property_batch, chunk_args)
            
            for i, batch_result in enumerate(batch_results):
                all_results.extend(batch_result)
                completed += len(batch_result)
                if (i + 1) % 5 == 0 or i == len(chunks) - 1:
                    print(f"  Progress: {completed:,} / {len(property_ids):,} ({completed/len(property_ids)*100:.1f}%)")
        
        # Update database
        updated = 0
        failed = 0
        
        print(f"\nUpdating database...")
        for prop_id, owner in all_results:
            if not owner:
                failed += 1
                continue
            
            prop = db.query(Property).filter(Property.id == prop_id).first()
            if prop:
                if not dry_run:
                    prop.owner_name = owner
                    updated += 1
                else:
                    print(f"  Would update {prop.parcel_id}: {owner}")
                    updated += 1
        
        if not dry_run:
            db.commit()
        
        print(f"\n✅ Updated {updated:,} properties with owners")
        if failed > 0:
            print(f"⚠️  {failed:,} properties still missing owners")
        
    finally:
        db.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--municipality', help='Filter by municipality')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode')
    args = parser.parse_args()
    
    fix_missing_owners(municipality=args.municipality, dry_run=args.dry_run)
