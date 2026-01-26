"""
Continuous CAMA Data Monitoring System
Can be run on-demand or scheduled (cron job)
Verifies all towns and reports any mismatches
"""
import sys
from pathlib import Path
from typing import Dict, List
from datetime import datetime
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from database import SessionLocal
from scripts.data_import.automated_cama_verification import (
    verify_all_towns,
    verify_town,
    get_all_municipalities
)
from scripts.data_import.cama_verification import (
    check_completeness
)

def monitor_all_towns(db: Session, raise_on_failure: bool = False) -> Dict:
    """
    Monitor all towns and generate comprehensive report
    Does not raise errors by default (for scheduled runs)
    """
    print("\n" + "=" * 80)
    print("CAMA DATA MONITORING - ALL TOWNS")
    print("=" * 80)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\nCRITICAL: 0% Mismatch Tolerance")
    
    try:
        # Verify all towns
        verification_result = verify_all_towns(db, raise_on_failure=raise_on_failure)
        
        # Check completeness for all towns
        municipalities = get_all_municipalities(db)
        completeness_results = []
        
        for municipality in municipalities:
            completeness = check_completeness(municipality, db)
            completeness_results.append(completeness)
        
        # Generate report
        print(f"\n{'='*80}")
        print("MONITORING REPORT")
        print(f"{'='*80}")
        
        print(f"\n📊 Verification Results:")
        print(f"  Total Towns: {verification_result['total_towns']:,}")
        print(f"  ✅ Verified (0% mismatch): {verification_result['verified_towns']:,}")
        print(f"  ❌ Failed: {verification_result['failed_towns']:,}")
        print(f"  ⚠️  Skipped: {verification_result['skipped_towns']:,}")
        print(f"  Overall Status: {verification_result['overall_status']}")
        
        print(f"\n📊 Completeness Results:")
        for comp in completeness_results:
            print(f"  {comp['municipality']}:")
            print(f"    Total Properties: {comp['total']:,}")
            print(f"    Completeness: {comp['completeness']:.1f}%")
            print(f"    Missing Owner: {comp['missing_owner']:,} ({comp['missing_owner_pct']:.1f}%)")
            print(f"    Missing Address: {comp['missing_address']:,} ({comp['missing_address_pct']:.1f}%)")
            print(f"    Missing Assessed: {comp['missing_assessed']:,} ({comp['missing_assessed_pct']:.1f}%)")
        
        # Alert if issues found
        if verification_result['failed_towns'] > 0:
            print(f"\n⚠️  ALERT: {verification_result['failed_towns']:,} town(s) failed verification!")
            print(f"   Mismatch rate must be 0% for all towns")
            if raise_on_failure:
                raise ValueError(f"Monitoring detected {verification_result['failed_towns']:,} town(s) with mismatches")
        else:
            print(f"\n✅ All towns verified successfully - 0% mismatch rate maintained")
        
        return {
            'timestamp': datetime.now().isoformat(),
            'verification': verification_result,
            'completeness': completeness_results,
            'status': verification_result['overall_status']
        }
        
    except Exception as e:
        print(f"\n❌ ERROR during monitoring: {str(e)}")
        if raise_on_failure:
            raise
        return {
            'timestamp': datetime.now().isoformat(),
            'status': 'ERROR',
            'error': str(e)
        }

def monitor_town(municipality: str, db: Session, raise_on_failure: bool = False) -> Dict:
    """
    Monitor specific town
    """
    print(f"\n{'='*80}")
    print(f"CAMA DATA MONITORING - {municipality}")
    print(f"{'='*80}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Verify town
        verification_result = verify_town(municipality, db, raise_on_failure=raise_on_failure)
        
        # Check completeness
        completeness_result = check_completeness(municipality, db)
        
        # Generate report
        print(f"\n{'='*80}")
        print("MONITORING REPORT")
        print(f"{'='*80}")
        
        print(f"\n📊 Verification Results:")
        print(f"  Status: {verification_result.get('status', 'UNKNOWN')}")
        print(f"  Total Properties: {verification_result.get('total', 0):,}")
        print(f"  Mismatched: {verification_result.get('mismatched', 0):,}")
        print(f"  Missing Data: {verification_result.get('missing_data', 0):,}")
        print(f"  Mismatch Rate: {verification_result.get('mismatch_rate', 0):.2f}%")
        
        print(f"\n📊 Completeness Results:")
        print(f"  Completeness: {completeness_result['completeness']:.1f}%")
        print(f"  Missing Owner: {completeness_result['missing_owner']:,} ({completeness_result['missing_owner_pct']:.1f}%)")
        print(f"  Missing Address: {completeness_result['missing_address']:,} ({completeness_result['missing_address_pct']:.1f}%)")
        print(f"  Missing Assessed: {completeness_result['missing_assessed']:,} ({completeness_result['missing_assessed_pct']:.1f}%)")
        
        if verification_result.get('status') != 'PASS':
            print(f"\n⚠️  ALERT: {municipality} failed verification!")
            if raise_on_failure:
                raise ValueError(f"{municipality} has mismatches")
        else:
            print(f"\n✅ {municipality} verified successfully - 0% mismatch rate")
        
        return {
            'timestamp': datetime.now().isoformat(),
            'municipality': municipality,
            'verification': verification_result,
            'completeness': completeness_result,
            'status': verification_result.get('status', 'UNKNOWN')
        }
        
    except Exception as e:
        print(f"\n❌ ERROR during monitoring: {str(e)}")
        if raise_on_failure:
            raise
        return {
            'timestamp': datetime.now().isoformat(),
            'municipality': municipality,
            'status': 'ERROR',
            'error': str(e)
        }

def generate_daily_report(db: Session) -> Dict:
    """
    Generate daily monitoring report
    Can be called by cron job
    """
    print("\n" + "=" * 80)
    print("DAILY CAMA DATA MONITORING REPORT")
    print("=" * 80)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d')}")
    
    result = monitor_all_towns(db, raise_on_failure=False)
    
    # Save report to file
    report_file = Path(__file__).parent.parent.parent / "logs" / f"cama_monitoring_{datetime.now().strftime('%Y%m%d')}.txt"
    report_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Note: In a real implementation, you might want to save structured data (JSON)
    # For now, the console output serves as the report
    
    return result

def main():
    """Main function for command-line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description='CAMA Data Monitoring System')
    parser.add_argument('--municipality', type=str, help='Monitor specific municipality')
    parser.add_argument('--all', action='store_true', help='Monitor all towns')
    parser.add_argument('--daily', action='store_true', help='Generate daily report')
    parser.add_argument('--raise-on-failure', action='store_true', help='Raise errors on failure (for alerts)')
    
    args = parser.parse_args()
    
    db = SessionLocal()
    
    try:
        if args.daily:
            generate_daily_report(db)
        elif args.municipality:
            monitor_town(args.municipality, db, raise_on_failure=args.raise_on_failure)
        elif args.all:
            monitor_all_towns(db, raise_on_failure=args.raise_on_failure)
        else:
            # Default: monitor all towns
            monitor_all_towns(db, raise_on_failure=args.raise_on_failure)
    finally:
        db.close()

if __name__ == "__main__":
    main()
