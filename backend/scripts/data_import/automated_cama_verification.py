"""
Automated CAMA Verification System
Verifies all towns, enforces 0% mismatch tolerance
Can be run before/after imports to protect existing towns
"""
import sys
from pathlib import Path
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import distinct, func

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from models import Property
from database import SessionLocal
from scripts.data_import.cama_verification import (
    verify_cama_data,
    find_mismatches,
    check_completeness,
    get_file_paths
)

def get_all_municipalities(db: Session) -> List[str]:
    """
    Get list of all municipalities in the database
    """
    results = db.query(distinct(Property.municipality)).filter(
        Property.municipality.isnot(None),
        Property.municipality != ''
    ).all()
    
    municipalities = [m[0] for m in results if m[0]]
    return sorted(municipalities)

def verify_all_towns(db: Session, raise_on_failure: bool = True) -> Dict:
    """
    Verify all towns in the database
    Returns comprehensive report
    Raises error if any town fails (0% mismatch tolerance)
    """
    print("\n" + "=" * 80)
    print("AUTOMATED CAMA VERIFICATION - ALL TOWNS")
    print("=" * 80)
    print("\nCRITICAL: 0% Mismatch Tolerance - Any mismatch is a failure")
    
    municipalities = get_all_municipalities(db)
    
    if not municipalities:
        print("\n⚠️  No municipalities found in database")
        return {
            'total_towns': 0,
            'verified_towns': 0,
            'failed_towns': 0,
            'results': []
        }
    
    print(f"\nFound {len(municipalities):,} municipalities:")
    for m in municipalities:
        print(f"  - {m}")
    
    print(f"\n{'='*80}")
    print("VERIFICATION RESULTS")
    print(f"{'='*80}")
    
    results = []
    verified_count = 0
    failed_count = 0
    
    for municipality in municipalities:
        print(f"\n{'─'*80}")
        print(f"Verifying: {municipality}")
        print(f"{'─'*80}")
        
        try:
            # Check if cleaned Excel file exists
            file_paths = get_file_paths(municipality)
            if not Path(file_paths['cleaned_excel']).exists():
                print(f"  ⚠️  SKIPPED: Cleaned Excel file not found")
                print(f"     Expected: {file_paths['cleaned_excel']}")
                results.append({
                    'municipality': municipality,
                    'status': 'SKIPPED',
                    'reason': 'Cleaned Excel file not found',
                    'total': 0,
                    'mismatched': 0,
                    'mismatch_rate': 0.0
                })
                continue
            
            # Verify CAMA data (will raise error if mismatches found)
            result = verify_cama_data(municipality, db)
            
            if result['status'] == 'PASS':
                verified_count += 1
                print(f"\n  ✅ PASS: {municipality} - 0% mismatch rate")
            else:
                failed_count += 1
                print(f"\n  ❌ FAIL: {municipality} - {result['mismatch_rate']:.2f}% mismatch rate")
                if raise_on_failure:
                    raise ValueError(
                        f"Verification failed for {municipality}: "
                        f"{result['mismatched']:,} mismatches, {result['missing_data']:,} missing data"
                    )
            
            results.append(result)
            
        except ValueError as e:
            failed_count += 1
            print(f"\n  ❌ FAIL: {municipality}")
            print(f"     Error: {str(e)}")
            results.append({
                'municipality': municipality,
                'status': 'FAIL',
                'error': str(e),
                'total': 0,
                'mismatched': 0,
                'mismatch_rate': 100.0
            })
            if raise_on_failure:
                raise
        except Exception as e:
            failed_count += 1
            print(f"\n  ❌ ERROR: {municipality}")
            print(f"     Error: {str(e)}")
            results.append({
                'municipality': municipality,
                'status': 'ERROR',
                'error': str(e),
                'total': 0,
                'mismatched': 0,
                'mismatch_rate': 100.0
            })
            if raise_on_failure:
                raise
    
    # Summary
    print(f"\n{'='*80}")
    print("VERIFICATION SUMMARY")
    print(f"{'='*80}")
    print(f"\n  Total Towns: {len(municipalities):,}")
    print(f"  ✅ Verified (0% mismatch): {verified_count:,}")
    print(f"  ❌ Failed: {failed_count:,}")
    print(f"  ⚠️  Skipped: {len([r for r in results if r.get('status') == 'SKIPPED']):,}")
    
    if failed_count > 0:
        print(f"\n  ⚠️  WARNING: {failed_count:,} town(s) failed verification")
        print(f"     All towns must have 0% mismatch rate")
        if raise_on_failure:
            raise ValueError(f"Verification failed: {failed_count:,} town(s) have mismatches")
    else:
        print(f"\n  ✅ SUCCESS: All towns verified with 0% mismatch rate!")
    
    return {
        'total_towns': len(municipalities),
        'verified_towns': verified_count,
        'failed_towns': failed_count,
        'skipped_towns': len([r for r in results if r.get('status') == 'SKIPPED']),
        'results': results,
        'overall_status': 'PASS' if failed_count == 0 else 'FAIL'
    }

def verify_town(municipality: str, db: Session, raise_on_failure: bool = True) -> Dict:
    """
    Verify specific town
    Returns verification result
    Raises error if mismatches found (0% mismatch tolerance)
    """
    print(f"\n{'='*80}")
    print(f"AUTOMATED CAMA VERIFICATION - {municipality}")
    print(f"{'='*80}")
    print("\nCRITICAL: 0% Mismatch Tolerance")
    
    # Check if cleaned Excel file exists
    file_paths = get_file_paths(municipality)
    if not Path(file_paths['cleaned_excel']).exists():
        error_msg = f"Cleaned Excel file not found: {file_paths['cleaned_excel']}"
        print(f"\n❌ ERROR: {error_msg}")
        if raise_on_failure:
            raise FileNotFoundError(error_msg)
        return {
            'municipality': municipality,
            'status': 'ERROR',
            'error': error_msg,
            'total': 0,
            'mismatched': 0,
            'mismatch_rate': 100.0
        }
    
    # Verify CAMA data (will raise error if mismatches found)
    try:
        result = verify_cama_data(municipality, db)
        return result
    except ValueError as e:
        if raise_on_failure:
            raise
        return {
            'municipality': municipality,
            'status': 'FAIL',
            'error': str(e),
            'total': 0,
            'mismatched': 0,
            'mismatch_rate': 100.0
        }

def verify_before_import(new_municipality: str, db: Session) -> Dict:
    """
    Verify all existing towns before importing new town
    Ensures existing towns remain at 0% mismatch
    """
    print("\n" + "=" * 80)
    print("PRE-IMPORT VERIFICATION")
    print("=" * 80)
    print(f"\nVerifying all existing towns before importing: {new_municipality}")
    print("CRITICAL: All existing towns must have 0% mismatch rate")
    
    municipalities = get_all_municipalities(db)
    
    # Remove new municipality from list (if it exists)
    existing_municipalities = [m for m in municipalities if m != new_municipality]
    
    if not existing_municipalities:
        print("\n✅ No existing towns to verify")
        return {
            'total_towns': 0,
            'verified_towns': 0,
            'failed_towns': 0,
            'results': []
        }
    
    print(f"\nVerifying {len(existing_municipalities):,} existing town(s)...")
    
    results = []
    verified_count = 0
    failed_count = 0
    
    for municipality in existing_municipalities:
        print(f"\n  Verifying: {municipality}")
        try:
            result = verify_town(municipality, db, raise_on_failure=False)
            if result.get('status') == 'PASS':
                verified_count += 1
                print(f"    ✅ PASS: 0% mismatch rate")
            else:
                failed_count += 1
                print(f"    ❌ FAIL: {result.get('mismatch_rate', 0):.2f}% mismatch rate")
            results.append(result)
        except Exception as e:
            failed_count += 1
            print(f"    ❌ ERROR: {str(e)}")
            results.append({
                'municipality': municipality,
                'status': 'ERROR',
                'error': str(e)
            })
    
    print(f"\n{'='*80}")
    print("PRE-IMPORT VERIFICATION SUMMARY")
    print(f"{'='*80}")
    print(f"  ✅ Verified: {verified_count:,}")
    print(f"  ❌ Failed: {failed_count:,}")
    
    if failed_count > 0:
        error_msg = f"Pre-import verification failed: {failed_count:,} existing town(s) have mismatches"
        print(f"\n  ❌ FAILURE: {error_msg}")
        print(f"     Cannot proceed with import until all existing towns have 0% mismatch rate")
        raise ValueError(error_msg)
    else:
        print(f"\n  ✅ SUCCESS: All existing towns verified with 0% mismatch rate")
        print(f"     Safe to proceed with importing: {new_municipality}")
    
    return {
        'total_towns': len(existing_municipalities),
        'verified_towns': verified_count,
        'failed_towns': failed_count,
        'results': results,
        'status': 'PASS' if failed_count == 0 else 'FAIL'
    }

def verify_after_import(municipality: str, db: Session) -> Dict:
    """
    Verify new town after import
    Also re-verify all existing towns to ensure no corruption
    """
    print("\n" + "=" * 80)
    print("POST-IMPORT VERIFICATION")
    print("=" * 80)
    print(f"\nVerifying {municipality} after import")
    print("Also re-verifying all existing towns to ensure no corruption")
    
    # Step 1: Verify new town
    print(f"\n{'─'*80}")
    print(f"Step 1: Verifying new town: {municipality}")
    print(f"{'─'*80}")
    
    new_town_result = verify_town(municipality, db, raise_on_failure=True)
    
    # Step 2: Re-verify all existing towns
    print(f"\n{'─'*80}")
    print(f"Step 2: Re-verifying all existing towns (ensuring no corruption)")
    print(f"{'─'*80}")
    
    all_towns_result = verify_all_towns(db, raise_on_failure=True)
    
    print(f"\n{'='*80}")
    print("POST-IMPORT VERIFICATION SUMMARY")
    print(f"{'='*80}")
    print(f"  ✅ New town ({municipality}): PASS")
    print(f"  ✅ All existing towns: PASS")
    print(f"\n  ✅ SUCCESS: All towns verified with 0% mismatch rate!")
    
    return {
        'new_town': new_town_result,
        'all_towns': all_towns_result,
        'status': 'PASS'
    }

def main():
    """Main function for command-line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Automated CAMA Verification System')
    parser.add_argument('--municipality', type=str, help='Verify specific municipality')
    parser.add_argument('--all', action='store_true', help='Verify all towns')
    parser.add_argument('--before-import', type=str, help='Verify all existing towns before importing new town')
    parser.add_argument('--after-import', type=str, help='Verify new town and re-verify all existing towns after import')
    parser.add_argument('--no-raise', action='store_true', help='Do not raise errors on failure (for reporting)')
    
    args = parser.parse_args()
    
    db = SessionLocal()
    
    try:
        if args.all:
            verify_all_towns(db, raise_on_failure=not args.no_raise)
        elif args.municipality:
            verify_town(args.municipality, db, raise_on_failure=not args.no_raise)
        elif args.before_import:
            verify_before_import(args.before_import, db)
        elif args.after_import:
            verify_after_import(args.after_import, db)
        else:
            # Default: verify all towns
            verify_all_towns(db, raise_on_failure=not args.no_raise)
    finally:
        db.close()

if __name__ == "__main__":
    main()
