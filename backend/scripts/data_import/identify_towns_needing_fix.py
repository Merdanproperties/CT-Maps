#!/usr/bin/env python3
"""
Identify towns that need fixing based on Excel reference counts
Shows towns where DB count is significantly different from Excel count
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pandas as pd
from database import SessionLocal
from models import Property
from sqlalchemy import func

def identify_towns_needing_fix():
    """Identify towns that need fixing"""
    # Read reference Excel
    excel_path = Path('/Users/jacobmermelstein/Desktop/CT Maps/Analysis scripts/169_towns_data_count_20260126_214921.xlsx')
    ref_df = pd.read_excel(excel_path, engine='openpyxl')
    
    # Get database counts
    db = SessionLocal()
    db_results = db.query(Property.municipality, func.count(Property.id).label('count')).group_by(Property.municipality).order_by(Property.municipality).all()
    db_towns = {muni.strip(): count for muni, count in db_results}
    
    print('='*100)
    print('TOWNS NEEDING FIX (DB count significantly different from Excel count)')
    print('='*100)
    print(f"{'Town':<25} {'DB Count':>12} {'Excel Count':>12} {'Difference':>12} {'% Match':>10} {'Status':<15}")
    print('-'*100)
    
    needs_fix = []
    for _, row in ref_df.iterrows():
        town = str(row['Town']).strip()
        excel_count = int(row['Post_Duplicate_Excel_Count']) if pd.notna(row['Post_Duplicate_Excel_Count']) else 0
        
        if excel_count == 0:
            continue  # Skip towns with no Excel file
        
        db_count = db_towns.get(town, 0)
        
        # Try case-insensitive match
        if db_count == 0:
            for db_town, db_cnt in db_towns.items():
                if db_town.upper() == town.upper():
                    db_count = db_cnt
                    break
        
        diff = db_count - excel_count
        pct = (db_count / excel_count * 100) if excel_count > 0 else 0
        
        # Flag if difference is > 5%
        if abs(pct - 100) > 5:
            status = "NEEDS FIX"
            needs_fix.append((town, db_count, excel_count, diff, pct))
        else:
            status = "OK"
        
        if abs(pct - 100) > 5 or db_count == 0:
            print(f"{town:<25} {db_count:>12,} {excel_count:>12,} {diff:>+12,} {pct:>9.1f}% {status:<15}")
    
    print('\n' + '='*100)
    print(f'SUMMARY: {len(needs_fix)} towns need fixing')
    print('='*100)
    
    # Sort by difference (most missing first)
    needs_fix.sort(key=lambda x: abs(x[3]), reverse=True)
    
    print('\nTop 30 towns needing fix (sorted by absolute difference):')
    print('-'*100)
    print(f"{'Town':<25} {'DB Count':>12} {'Excel Count':>12} {'Difference':>12} {'% Match':>10}")
    print('-'*100)
    for town, db_cnt, excel_cnt, diff, pct in needs_fix[:30]:
        print(f"{town:<25} {db_cnt:>12,} {excel_cnt:>12,} {diff:>+12,} {pct:>9.1f}%")
    
    db.close()
    
    return needs_fix

if __name__ == "__main__":
    identify_towns_needing_fix()
