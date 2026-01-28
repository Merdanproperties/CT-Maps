"""
Script to count properties per town in the database
Shows breakdown to verify total count and check for duplicates
"""
import sys
from pathlib import Path
from sqlalchemy import func, text
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from database import SessionLocal
from models import Property

def count_by_town():
    """Count properties per town and show detailed breakdown"""
    db = SessionLocal()
    
    try:
        print("=" * 80)
        print("PROPERTY COUNT BY TOWN")
        print("=" * 80)
        
        # Total count
        total = db.query(Property).count()
        print(f"\n📊 TOTAL PROPERTIES: {total:,}")
        
        # Count by town
        town_counts = db.query(
            Property.municipality,
            func.count(Property.id).label('count')
        ).filter(
            Property.municipality.isnot(None)
        ).group_by(
            Property.municipality
        ).order_by(
            func.count(Property.id).desc()
        ).all()
        
        print(f"\n📋 PROPERTIES BY TOWN ({len(town_counts)} towns):")
        print("-" * 80)
        print(f"{'Town':<30} {'Count':>12} {'Percentage':>12}")
        print("-" * 80)
        
        running_total = 0
        for town, count in town_counts:
            percentage = (count / total * 100) if total > 0 else 0
            print(f"{town:<30} {count:>12,} {percentage:>11.2f}%")
            running_total += count
        
        # Check for null municipalities
        null_count = db.query(Property).filter(Property.municipality.is_(None)).count()
        if null_count > 0:
            print(f"{'[NULL/EMPTY]':<30} {null_count:>12,} {(null_count/total*100):>11.2f}%")
            running_total += null_count
        
        print("-" * 80)
        print(f"{'TOTAL':<30} {running_total:>12,} {'100.00':>12}%")
        
        # Verify no duplicates
        print("\n" + "=" * 80)
        print("DUPLICATE CHECK")
        print("=" * 80)
        
        # Check for duplicate parcel_ids
        duplicate_parcels = db.query(
            Property.parcel_id,
            func.count(Property.id).label('count')
        ).group_by(
            Property.parcel_id
        ).having(
            func.count(Property.id) > 1
        ).all()
        
        if duplicate_parcels:
            print(f"⚠️  WARNING: Found {len(duplicate_parcels)} duplicate parcel_ids!")
            for parcel_id, count in duplicate_parcels[:10]:
                print(f"  {parcel_id}: {count} occurrences")
            if len(duplicate_parcels) > 10:
                print(f"  ... and {len(duplicate_parcels) - 10} more")
        else:
            print("✅ No duplicate parcel_ids found (unique constraint working)")
        
        # Summary statistics
        print("\n" + "=" * 80)
        print("SUMMARY STATISTICS")
        print("=" * 80)
        
        unique_towns = db.query(func.count(func.distinct(Property.municipality))).scalar()
        unique_parcels = db.query(func.count(func.distinct(Property.parcel_id))).scalar()
        
        print(f"Total properties: {total:,}")
        print(f"Unique parcel_ids: {unique_parcels:,}")
        print(f"Unique towns: {unique_towns}")
        
        if total != unique_parcels:
            print(f"⚠️  WARNING: Total count ({total:,}) != Unique parcel_ids ({unique_parcels:,})")
            print(f"   Difference: {total - unique_parcels:,} rows")
        else:
            print("✅ Total count matches unique parcel_ids")
        
        return {
            'total': total,
            'towns': len(town_counts),
            'town_counts': {town: count for town, count in town_counts},
            'duplicates': len(duplicate_parcels)
        }
        
    finally:
        db.close()

if __name__ == "__main__":
    count_by_town()
