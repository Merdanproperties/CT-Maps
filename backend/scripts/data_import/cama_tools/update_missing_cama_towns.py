#!/usr/bin/env python3
"""
Update CAMA data for towns that have properties but 0 CAMA updates
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from database import SessionLocal
from scripts.data_import.cama_tools.cama_update import update_all_cama_from_cleaned_excel
from scripts.data_import.verification.cama_verification import get_file_paths

# Towns that need CAMA updates (from user's data)
TOWNS_NEEDING_CAMA = [
    'New Milford',
    'Bristol',
    'Bethel',
    'New Canaan',
    'Monroe',
    'Orange',
    'North Branford',
    'New Fairfield',
    'Barkhamsted',
    'North canaan',
    'Bozrah',
    'Morris',
    'Bridgewater',
    'Franklin',
    'Canaan',
    'New hartford',
    'Bethlehem'
]

def main():
    print("=" * 80)
    print("UPDATING CAMA DATA FOR TOWNS WITH 0 CAMA UPDATES")
    print("=" * 80)
    print(f"\nTowns to update: {len(TOWNS_NEEDING_CAMA)}")
    
    results = {
        'successful': [],
        'failed': [],
        'no_excel': []
    }
    
    for i, town in enumerate(TOWNS_NEEDING_CAMA, 1):
        print(f"\n{'='*80}")
        print(f"Processing {i}/{len(TOWNS_NEEDING_CAMA)}: {town}")
        print(f"{'='*80}")
        
        db = SessionLocal()
        try:
            # Check if Excel file exists
            file_paths = get_file_paths(town)
            if not Path(file_paths['cleaned_excel']).exists():
                print(f"⚠️  Excel file not found: {file_paths['cleaned_excel']}")
                results['no_excel'].append(town)
                continue
            
            # Update CAMA data
            result = update_all_cama_from_cleaned_excel(town, db, dry_run=False)
            
            if result.get('updated', 0) > 0:
                print(f"✅ Successfully updated {result.get('updated', 0):,} properties")
                results['successful'].append((town, result.get('updated', 0)))
            else:
                print(f"⚠️  No properties updated")
                results['failed'].append((town, "No properties updated"))
                
        except Exception as e:
            print(f"❌ Error updating {town}: {e}")
            results['failed'].append((town, str(e)))
            if db:
                try:
                    db.rollback()
                except:
                    pass
        finally:
            if db:
                db.close()
    
    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    print(f"✅ Successful: {len(results['successful'])}")
    for town, count in results['successful']:
        print(f"  {town}: {count:,} properties updated")
    
    print(f"\n❌ Failed: {len(results['failed'])}")
    for town, error in results['failed']:
        print(f"  {town}: {error}")
    
    print(f"\n⚠️  No Excel file: {len(results['no_excel'])}")
    for town in results['no_excel']:
        print(f"  {town}")

if __name__ == "__main__":
    main()
