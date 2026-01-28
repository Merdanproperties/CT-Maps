#!/usr/bin/env python3
"""
Quick progress checker for batch import
Run this in your terminal to see current progress
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from database import SessionLocal
from models import Property
from sqlalchemy import func

# Read expected towns (list lives in 134_towns_output)
with open(Path(__file__).parent / '134_towns_output' / 'towns_to_import.txt', 'r') as f:
    expected_towns = [line.strip() for line in f if line.strip()]

db = SessionLocal()
try:
    # Get imported towns
    imported = db.query(
        func.upper(Property.municipality).label('town'),
        func.count(Property.id).label('count')
    ).filter(
        func.upper(Property.municipality).in_([t.upper() for t in expected_towns])
    ).group_by(func.upper(Property.municipality)).all()
    
    imported_towns = {t[0].upper(): t[1] for t in imported}
    
    print('=' * 80)
    print('BATCH IMPORT PROGRESS')
    print('=' * 80)
    print(f'Expected towns: {len(expected_towns)}')
    print(f'Imported towns: {len(imported_towns)}')
    print(f'Progress: {len(imported_towns)}/{len(expected_towns)} ({len(imported_towns)/len(expected_towns)*100:.1f}%)')
    print(f'\nTotal properties imported: {sum(imported_towns.values()):,}')
    
    if imported_towns:
        print(f'\nRecently imported towns (last 10):')
        for town, count in list(imported_towns.items())[-10:]:
            print(f'  ✅ {town}: {count:,} properties')
    
    remaining = len(expected_towns) - len(imported_towns)
    if remaining > 0:
        print(f'\n⏳ {remaining} towns remaining...')
finally:
    db.close()
