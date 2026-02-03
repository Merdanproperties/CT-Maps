#!/usr/bin/env python3
"""
Compare database counts to Post Duplicate Excel counts from reference file
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import pandas as pd
from database import SessionLocal
from models import Property
from sqlalchemy import func

def compare_counts():
    """Compare database counts to Excel reference counts"""
    # Read reference Excel
    excel_path = Path('/Users/jacobmermelstein/Desktop/CT Maps/Analysis scripts/169_towns_data_count_20260126_214921.xlsx')
    ref_df = pd.read_excel(excel_path, engine='openpyxl')
    
    # Get database counts
    db = SessionLocal()
    db_results = db.query(Property.municipality, func.count(Property.id).label('count')).group_by(Property.municipality).order_by(Property.municipality).all()
    db_towns = {muni.strip(): count for muni, count in db_results}
    
    print('='*100)
    print('COMPARISON: Database vs Post Duplicate Excel Count')
    print('='*100)
    print(f"{'Town':<25} {'DB Count':>12} {'Excel Count':>12} {'Difference':>12} {'% Match':>10}")
    print('-'*100)
    
    # Check Bristol specifically
    bristol_ref = ref_df[ref_df['Town'].str.strip().str.upper() == 'BRISTOL']
    if not bristol_ref.empty:
        excel_count = int(bristol_ref['Post_Duplicate_Excel_Count'].iloc[0])
        db_count = db_towns.get('Bristol', 0)
        diff = db_count - excel_count
        pct = (db_count / excel_count * 100) if excel_count > 0 else 0
        print(f"{'Bristol':<25} {db_count:>12,} {excel_count:>12,} {diff:>+12,} {pct:>9.1f}%")
        print('-'*100)
    
    # Show all towns with significant differences
    print('\nTowns with largest differences (DB vs Excel):')
    print('-'*100)
    differences = []
    for _, row in ref_df.iterrows():
        town = str(row['Town']).strip()
        excel_count = int(row['Post_Duplicate_Excel_Count']) if pd.notna(row['Post_Duplicate_Excel_Count']) else 0
        db_count = db_towns.get(town, 0)
        
        # Try case-insensitive match
        if db_count == 0:
            for db_town, db_cnt in db_towns.items():
                if db_town.upper() == town.upper():
                    db_count = db_cnt
                    break
        
        if excel_count > 0:
            diff = db_count - excel_count
            pct_diff = abs(diff / excel_count * 100) if excel_count > 0 else 0
            differences.append((town, db_count, excel_count, diff, pct_diff))
    
    # Sort by absolute difference
    differences.sort(key=lambda x: abs(x[3]), reverse=True)
    
    print(f"{'Town':<25} {'DB Count':>12} {'Excel Count':>12} {'Difference':>12} {'% Diff':>10}")
    print('-'*100)
    for town, db_cnt, excel_cnt, diff, pct_diff in differences[:50]:
        print(f"{town:<25} {db_cnt:>12,} {excel_cnt:>12,} {diff:>+12,} {pct_diff:>9.1f}%")
    
    # Summary
    print('\n' + '='*100)
    print('SUMMARY')
    print('='*100)
    
    total_excel = ref_df['Post_Duplicate_Excel_Count'].sum()
    total_db = sum(db_towns.values())
    
    print(f"Total Excel Count: {total_excel:,}")
    print(f"Total DB Count: {total_db:,}")
    print(f"Difference: {total_db - total_excel:+,}")
    
    # Count towns that are close (within 5%)
    close_count = 0
    for town, db_cnt, excel_cnt, diff, pct_diff in differences:
        if pct_diff <= 5.0:
            close_count += 1
    
    print(f"\nTowns within 5% of Excel count: {close_count}/{len(differences)}")
    
    db.close()

if __name__ == "__main__":
    compare_counts()
