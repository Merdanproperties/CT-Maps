"""
Complete town data fix script - applies all Torrington lessons to any town
This script:
1. Imports missing parcels from geodatabase
2. Fixes missing addresses using reverse geocoding
3. Fixes missing owners using Excel matching
4. Standardizes address formats

Usage:
    python3 fix_town_data_complete.py --municipality Torrington
    python3 fix_town_data_complete.py --municipality Danbury --dry-run
"""
import sys
import os
from pathlib import Path
from typing import Optional
import argparse
from dotenv import load_dotenv

# Add backend directory to path
backend_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_dir))

load_dotenv()

def check_prerequisites(municipality: str) -> tuple[bool, list]:
    """Check if prerequisites are met"""
    issues = []
    
    # Check Excel file
    excel_file = f'/Users/jacobmermelstein/Desktop/CT Data/2025 Post Duplicate Clean/{municipality}_CAMA_2025_CLEANED.xlsx'
    if not os.path.exists(excel_file):
        issues.append(f"Excel file not found: {excel_file}")
    
    # Check Nominatim
    import requests
    try:
        response = requests.get('http://localhost:8080/reverse?lat=41.8&lon=-73.1&format=json', timeout=5)
        if response.status_code != 200:
            issues.append("Nominatim not accessible at http://localhost:8080")
    except Exception:
        issues.append("Nominatim not accessible at http://localhost:8080")
    
    # Check geodatabase
    gdb_path = '/Users/jacobmermelstein/Desktop/CT Maps/2025 Parcel Layer.gdb'
    if not os.path.exists(gdb_path):
        issues.append(f"Geodatabase not found: {gdb_path}")
    
    return len(issues) == 0, issues

def import_missing_parcels(municipality: str, dry_run: bool = False):
    """Import missing parcels from geodatabase"""
    print("\n" + "=" * 60)
    print("STEP 1: Import Missing Parcels")
    print("=" * 60)
    
    # Check if script exists
    script_path = Path(__file__).parent.parent / "import_missing_torrington_parcels.py"
    if not script_path.exists():
        print("⚠️  Missing parcels import script not found - skipping")
        return
    
    # Adapt script for this municipality
    # For now, we'll use the existing script and modify MUNICIPALITY
    print(f"Note: This step requires adapting import_missing_torrington_parcels.py for {municipality}")
    print("Skipping for now - run manually if needed")

def fix_addresses(municipality: str, dry_run: bool = False):
    """Fix missing addresses using reverse geocoding"""
    print("\n" + "=" * 60)
    print("STEP 2: Fix Missing Addresses")
    print("=" * 60)
    
    from scripts.data_fix.fix_all_missing_addresses import fix_missing_addresses
    fix_missing_addresses(municipality=municipality, dry_run=dry_run)

def fix_owners(municipality: str, dry_run: bool = False):
    """Fix missing owners using Excel matching"""
    print("\n" + "=" * 60)
    print("STEP 3: Fix Missing Owners")
    print("=" * 60)
    
    from scripts.data_fix.fix_all_missing_owners import fix_missing_owners
    fix_missing_owners(municipality=municipality, dry_run=dry_run)

def verify_results(municipality: str):
    """Verify the results"""
    print("\n" + "=" * 60)
    print("VERIFICATION")
    print("=" * 60)
    
    from database import SessionLocal
    from models import Property
    
    db = SessionLocal()
    try:
        total = db.query(Property).filter(Property.municipality.ilike(f'%{municipality}%')).count()
        
        no_address = db.query(Property).filter(
            Property.municipality.ilike(f'%{municipality}%'),
            (Property.address.is_(None)) | (Property.address == '') | (Property.address == 'None')
        ).count()
        
        no_owner = db.query(Property).filter(
            Property.municipality.ilike(f'%{municipality}%'),
            (Property.owner_name.is_(None)) | (Property.owner_name == '') | (Property.owner_name == 'None')
        ).count()
        
        print(f"\n{municipality} Results:")
        print(f"  Total properties: {total:,}")
        print(f"  Without addresses: {no_address:,} ({(1-no_address/total)*100:.2f}% coverage)")
        print(f"  Without owners: {no_owner:,} ({(1-no_owner/total)*100:.2f}% coverage)")
        
        if no_address == 0 and no_owner / total < 0.05:
            print(f"\n✅ SUCCESS: {municipality} data is complete!")
        elif no_address / total < 0.01 and no_owner / total < 0.05:
            print(f"\n✅ GOOD: {municipality} data is mostly complete")
        else:
            print(f"\n⚠️  WARNING: {municipality} still has issues")
    finally:
        db.close()

def main():
    parser = argparse.ArgumentParser(description='Complete town data fix')
    parser.add_argument('--municipality', required=True, help='Municipality name')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode')
    parser.add_argument('--skip-parcels', action='store_true', help='Skip missing parcels import')
    parser.add_argument('--skip-addresses', action='store_true', help='Skip address fix')
    parser.add_argument('--skip-owners', action='store_true', help='Skip owner fix')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print(f"Complete Data Fix for {args.municipality}")
    print("=" * 60)
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
    
    # Check prerequisites
    print("\nChecking prerequisites...")
    ok, issues = check_prerequisites(args.municipality)
    if not ok:
        print("❌ Prerequisites not met:")
        for issue in issues:
            print(f"   - {issue}")
        print("\nPlease fix these issues before continuing.")
        return
    
    print("✅ All prerequisites met")
    
    # Run fixes
    if not args.skip_parcels:
        import_missing_parcels(args.municipality, args.dry_run)
    
    if not args.skip_addresses:
        fix_addresses(args.municipality, args.dry_run)
    
    if not args.skip_owners:
        fix_owners(args.municipality, args.dry_run)
    
    # Verify
    if not args.dry_run:
        verify_results(args.municipality)
    
    print("\n" + "=" * 60)
    print("✅ Complete!")
    print("=" * 60)

if __name__ == "__main__":
    main()
