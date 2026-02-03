"""
Standard Import Workflow with Built-in Verification
Protects existing towns and ensures 0% mismatch rate
"""
import sys
from pathlib import Path
from typing import Dict, Optional
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from database import SessionLocal
from scripts.data_import.verification.automated_cama_verification import (
    verify_before_import,
    verify_after_import,
    verify_town
)
from scripts.data_import.cama_tools.cama_update import (
    update_all_cama_from_cleaned_excel,
    fix_mismatches
)

def import_with_verification(
    municipality: str,
    db: Session,
    import_properties_func=None,
    import_cama_func=None,
    dry_run: bool = False
) -> Dict:
    """
    Standard import workflow with built-in verification
    
    Steps:
    1. Pre-import verification (check existing towns)
    2. Import new town properties
    3. Import/update CAMA data from cleaned Excel
    4. Post-import verification (check new town)
    5. Re-verify all existing towns (ensure no corruption)
    6. Fix any mismatches (0% tolerance)
    7. Final verification (all towns)
    8. Generate report
    
    Args:
        municipality: Name of municipality to import
        db: Database session
        import_properties_func: Optional function to import properties from geodatabase
        import_cama_func: Optional function to import CAMA data
        dry_run: If True, don't make database changes
    
    Returns:
        Dict with import and verification results
    """
    print("\n" + "=" * 80)
    print("STANDARD IMPORT WORKFLOW WITH VERIFICATION")
    print("=" * 80)
    print(f"\nImporting: {municipality}")
    print("CRITICAL: 0% Mismatch Tolerance - All steps must pass")
    
    if dry_run:
        print("\n🔍 DRY RUN MODE - No database changes will be made")
    
    results = {
        'municipality': municipality,
        'pre_import_verification': None,
        'properties_imported': 0,
        'cama_updated': None,
        'post_import_verification': None,
        'mismatch_fix': None,
        'final_verification': None,
        'status': 'PENDING'
    }
    
    try:
        # Step 1: Pre-import verification
        print(f"\n{'='*80}")
        print("STEP 1: Pre-Import Verification")
        print(f"{'='*80}")
        print("Verifying all existing towns (must have 0% mismatch rate)")
        
        pre_import_result = verify_before_import(municipality, db)
        results['pre_import_verification'] = pre_import_result
        
        if pre_import_result['status'] != 'PASS':
            raise ValueError("Pre-import verification failed - cannot proceed")
        
        print("\n✅ Pre-import verification PASSED - All existing towns verified")
        
        # Step 2: Import properties from geodatabase (if function provided)
        if import_properties_func:
            print(f"\n{'='*80}")
            print("STEP 2: Import Properties from Geodatabase")
            print(f"{'='*80}")
            
            if not dry_run:
                imported_count = import_properties_func(municipality, db)
                results['properties_imported'] = imported_count
                print(f"\n✅ Imported {imported_count:,} properties")
            else:
                print("\n🔍 DRY RUN: Would import properties")
        else:
            print(f"\n{'='*80}")
            print("STEP 2: Import Properties from Geodatabase")
            print(f"{'='*80}")
            print("⚠️  No import_properties_func provided - skipping property import")
            print("   (Properties may already be imported)")
        
        # Step 3: Import/update CAMA data from cleaned Excel
        print(f"\n{'='*80}")
        print("STEP 3: Import/Update CAMA Data from Cleaned Excel")
        print(f"{'='*80}")
        print("CRITICAL: Cleaned Excel is SINGLE SOURCE OF TRUTH")
        
        if import_cama_func:
            if not dry_run:
                cama_result = import_cama_func(municipality, db)
                results['cama_updated'] = cama_result
            else:
                print("\n🔍 DRY RUN: Would import/update CAMA data")
        else:
            # Use standard CAMA update
            cama_result = update_all_cama_from_cleaned_excel(municipality, db, dry_run=dry_run)
            results['cama_updated'] = cama_result
            print(f"\n✅ Updated {cama_result['updated']:,} properties with CAMA data")
        
        # Step 4: Post-import verification (new town)
        print(f"\n{'='*80}")
        print("STEP 4: Post-Import Verification (New Town)")
        print(f"{'='*80}")
        print(f"Verifying {municipality} (must have 0% mismatch rate)")
        
        new_town_result = verify_town(municipality, db, raise_on_failure=True)
        
        if new_town_result['status'] != 'PASS':
            print(f"\n⚠️  New town verification failed - attempting to fix mismatches...")
            
            # Step 5: Fix mismatches
            print(f"\n{'='*80}")
            print("STEP 5: Fix Mismatches")
            print(f"{'='*80}")
            
            fix_result = fix_mismatches(municipality, db, dry_run=dry_run)
            results['mismatch_fix'] = fix_result
            
            # Re-verify after fix
            new_town_result = verify_town(municipality, db, raise_on_failure=True)
        
        results['post_import_verification'] = {
            'new_town': new_town_result
        }
        
        print("\n✅ Post-import verification PASSED - New town verified")
        
        # Step 6: Re-verify all existing towns (ensure no corruption)
        print(f"\n{'='*80}")
        print("STEP 6: Re-Verify All Existing Towns")
        print(f"{'='*80}")
        print("Ensuring no existing towns were corrupted during import")
        
        from scripts.data_import.verification.automated_cama_verification import verify_all_towns
        all_towns_result = verify_all_towns(db, raise_on_failure=True)
        
        results['post_import_verification']['all_towns'] = all_towns_result
        
        if all_towns_result['overall_status'] != 'PASS':
            raise ValueError("Re-verification of existing towns failed - data corruption detected")
        
        print("\n✅ Re-verification PASSED - All existing towns still at 0% mismatch")
        
        # Step 7: Final verification (all towns)
        print(f"\n{'='*80}")
        print("STEP 7: Final Verification (All Towns)")
        print(f"{'='*80}")
        
        final_result = verify_all_towns(db, raise_on_failure=True)
        results['final_verification'] = final_result
        
        print("\n✅ Final verification PASSED - All towns at 0% mismatch rate")
        
        # Step 8: Generate report
        print(f"\n{'='*80}")
        print("IMPORT COMPLETE - SUMMARY REPORT")
        print(f"{'='*80}")
        print(f"\n  Municipality: {municipality}")
        print(f"  Properties Imported: {results['properties_imported']:,}")
        if results['cama_updated']:
            print(f"  Properties Updated: {results['cama_updated']['updated']:,}")
            print(f"  Fields Updated: {results['cama_updated']['total_fields']:,}")
        print(f"  Pre-Import Verification: ✅ PASS")
        print(f"  Post-Import Verification: ✅ PASS")
        print(f"  Final Verification: ✅ PASS")
        print(f"\n  ✅ SUCCESS: Import completed with 0% mismatch rate!")
        
        results['status'] = 'SUCCESS'
        
        return results
        
    except Exception as e:
        print(f"\n{'='*80}")
        print("IMPORT FAILED")
        print(f"{'='*80}")
        print(f"\n❌ ERROR: {str(e)}")
        print(f"\n  Import workflow stopped due to verification failure")
        print(f"  0% mismatch tolerance requires all steps to pass")
        
        results['status'] = 'FAILED'
        results['error'] = str(e)
        
        if not dry_run:
            raise
        
        return results

def main():
    """Main function for command-line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Import with Verification Workflow')
    parser.add_argument('municipality', type=str, help='Municipality to import')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode (no database changes)')
    
    args = parser.parse_args()
    
    db = SessionLocal()
    
    try:
        result = import_with_verification(
            args.municipality,
            db,
            dry_run=args.dry_run
        )
        
        if result['status'] == 'SUCCESS':
            print("\n✅ Import workflow completed successfully!")
        else:
            print("\n❌ Import workflow failed!")
            sys.exit(1)
            
    finally:
        db.close()

if __name__ == "__main__":
    main()
