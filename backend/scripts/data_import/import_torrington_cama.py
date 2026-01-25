"""
Import Torrington CAMA data using the hybrid approach
Adapted from import_cama_2025_hybrid.py for Torrington
"""
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

# Import the main import function and modify file paths
from scripts.data_import.import_bridgeport_cama_2025 import (
    read_cleaned_excel,
    read_raw_csv,
    match_and_combine,
    import_to_database,
    generate_coverage_report,
    normalize_address
)
from database import SessionLocal
from datetime import datetime

# File paths for Torrington
CLEANED_FILE = "/Users/jacobmermelstein/Desktop/CT Data/2025 Post Duplicate Clean/Torrington_CAMA_2025_CLEANED.xlsx"
RAW_CSV_FILE = "/Users/jacobmermelstein/Desktop/CT Data/2025 Parcel Collection/Torrington_CAMA_2025.csv"
MUNICIPALITY = "Torrington"

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Import Torrington 2025 CAMA data')
    parser.add_argument('--limit', type=int, help='Limit number of records to import (for testing)')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode - no database changes')
    parser.add_argument('--parallel', action='store_true', default=True, help='Use parallel processing (default: True)')
    parser.add_argument('--no-parallel', dest='parallel', action='store_false', help='Disable parallel processing')
    args = parser.parse_args()
    
    start_time = datetime.now()
    
    print("\n" + "=" * 60)
    print("Torrington 2025 CAMA Data Import - Hybrid Approach")
    print("=" * 60)
    print(f"Start time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - No database changes will be made")
    
    if args.limit:
        print(f"📊 Test mode: Limiting to {args.limit} records")
    
    db = SessionLocal()
    
    try:
        # Step 1: Read cleaned Excel file
        cleaned_df = read_cleaned_excel(CLEANED_FILE, limit=args.limit)
        
        # Step 2: Read raw CSV file
        raw_df, raw_lookup = read_raw_csv(RAW_CSV_FILE)
        
        # Step 3: Match and combine
        combined_records = match_and_combine(cleaned_df, raw_lookup)
        
        # Step 4: Import to database
        import_to_database(combined_records, db, MUNICIPALITY, dry_run=args.dry_run, use_parallel=args.parallel)
        
        # Step 5: Generate coverage report
        if not args.dry_run:
            report_file = f"logs/torrington_cama_coverage_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            generate_coverage_report(db, MUNICIPALITY, report_file)
        
        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()
        print("\n" + "=" * 60)
        print("✅ Import completed successfully!")
        print(f"End time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Total elapsed time: {elapsed/60:.1f} minutes ({elapsed:.1f} seconds)")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()
