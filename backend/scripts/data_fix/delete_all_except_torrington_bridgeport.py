#!/usr/bin/env python3
"""
Delete all database data except Torrington and Bridgeport properties.

This script will:
1. Show a preview of what will be deleted
2. Ask for confirmation
3. Delete property comments, sales, and properties for all towns except Torrington and Bridgeport
"""
import sys
from pathlib import Path
from sqlalchemy import func

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from database import SessionLocal
from models import Property, Sale, PropertyComment

KEEP_TOWNS = ["Torrington", "Bridgeport"]

def preview_deletion():
    """Show what will be deleted"""
    db = SessionLocal()
    try:
        print("=" * 80)
        print("DELETION PREVIEW")
        print("=" * 80)
        
        # Get all properties
        all_properties = db.query(Property).count()
        
        # Get properties to keep
        keep_properties = db.query(Property).filter(
            Property.municipality.in_(KEEP_TOWNS)
        ).count()
        
        # Get properties to delete
        delete_properties = db.query(Property).filter(
            ~Property.municipality.in_(KEEP_TOWNS)
        ).count()
        
        print(f"\n📊 PROPERTIES:")
        print(f"   Total: {all_properties:,}")
        print(f"   Keeping: {keep_properties:,} (Torrington + Bridgeport)")
        print(f"   Deleting: {delete_properties:,}")
        
        # Get property IDs to delete
        property_ids_to_delete = [
            p.id for p in db.query(Property.id).filter(
                ~Property.municipality.in_(KEEP_TOWNS)
            ).all()
        ]
        
        # Count related data
        if property_ids_to_delete:
            comments_to_delete = db.query(PropertyComment).filter(
                PropertyComment.property_id.in_(property_ids_to_delete)
            ).count()
            
            sales_to_delete = db.query(Sale).filter(
                Sale.property_id.in_(property_ids_to_delete)
            ).count()
        else:
            comments_to_delete = 0
            sales_to_delete = 0
        
        print(f"\n📝 RELATED DATA:")
        print(f"   Property Comments to delete: {comments_to_delete:,}")
        print(f"   Sales records to delete: {sales_to_delete:,}")
        
        # Show breakdown by town
        print(f"\n📋 BREAKDOWN BY TOWN:")
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
        
        print(f"\n   {'Town':<30} {'Count':>12} {'Status':>12}")
        print(f"   {'-'*30} {'-'*12} {'-'*12}")
        for town, count in town_counts:
            status = "KEEP" if town in KEEP_TOWNS else "DELETE"
            print(f"   {town:<30} {count:>12,} {status:>12}")
        
        null_count = db.query(Property).filter(Property.municipality.is_(None)).count()
        if null_count > 0:
            print(f"   {'[NULL/EMPTY]':<30} {null_count:>12,} {'DELETE':>12}")
        
        print("\n" + "=" * 80)
        
        return {
            'properties_to_delete': delete_properties,
            'comments_to_delete': comments_to_delete,
            'sales_to_delete': sales_to_delete,
            'property_ids': property_ids_to_delete
        }
    finally:
        db.close()

def delete_data(dry_run=False):
    """Delete all data except Torrington and Bridgeport"""
    db = SessionLocal()
    try:
        if dry_run:
            print("\n🔍 DRY RUN MODE - No changes will be made")
        
        # Get property IDs to delete
        properties_to_delete = db.query(Property).filter(
            ~Property.municipality.in_(KEEP_TOWNS)
        ).all()
        
        property_ids_to_delete = [p.id for p in properties_to_delete]
        
        if not property_ids_to_delete:
            print("\n✅ No properties to delete!")
            return
        
        print(f"\n🗑️  DELETING DATA...")
        
        # Delete property comments first (has foreign key constraint)
        print(f"\n   1. Deleting property comments...")
        comments_deleted = 0
        if property_ids_to_delete:
            comments = db.query(PropertyComment).filter(
                PropertyComment.property_id.in_(property_ids_to_delete)
            ).all()
            comments_deleted = len(comments)
            if not dry_run:
                for comment in comments:
                    db.delete(comment)
                db.flush()
        print(f"      ✅ Deleted {comments_deleted:,} property comments")
        
        # Delete sales records
        print(f"\n   2. Deleting sales records...")
        sales_deleted = 0
        if property_ids_to_delete:
            sales = db.query(Sale).filter(
                Sale.property_id.in_(property_ids_to_delete)
            ).all()
            sales_deleted = len(sales)
            if not dry_run:
                for sale in sales:
                    db.delete(sale)
                db.flush()
        print(f"      ✅ Deleted {sales_deleted:,} sales records")
        
        # Delete properties
        print(f"\n   3. Deleting properties...")
        properties_deleted = len(properties_to_delete)
        if not dry_run:
            for prop in properties_to_delete:
                db.delete(prop)
            db.commit()
        else:
            print(f"      (Would delete {properties_deleted:,} properties)")
        print(f"      ✅ Deleted {properties_deleted:,} properties")
        
        print("\n" + "=" * 80)
        print("✅ DELETION COMPLETE!")
        print("=" * 80)
        print(f"\nRemaining in database:")
        remaining = db.query(Property).filter(
            Property.municipality.in_(KEEP_TOWNS)
        ).count()
        print(f"   Properties: {remaining:,}")
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()

def main():
    """Main function"""
    print("=" * 80)
    print("DELETE ALL DATA EXCEPT TORRINGTON AND BRIDGEPORT")
    print("=" * 80)
    print(f"\n⚠️  WARNING: This will permanently delete all properties,")
    print(f"   property comments, and sales records for towns other than:")
    print(f"   - Torrington")
    print(f"   - Bridgeport")
    print(f"\nThis action CANNOT be undone!")
    
    # Show preview
    preview = preview_deletion()
    
    if preview['properties_to_delete'] == 0:
        print("\n✅ No data to delete - database already contains only Torrington and Bridgeport!")
        return
    
    # Ask for confirmation
    print("\n" + "=" * 80)
    response = input("\n⚠️  Type 'DELETE' to confirm deletion (or 'dry-run' for a test): ").strip()
    
    if response == 'DELETE':
        print("\n🗑️  Proceeding with deletion...")
        delete_data(dry_run=False)
    elif response.lower() == 'dry-run':
        print("\n🔍 Running in dry-run mode...")
        delete_data(dry_run=True)
    else:
        print("\n❌ Deletion cancelled.")

if __name__ == "__main__":
    main()
