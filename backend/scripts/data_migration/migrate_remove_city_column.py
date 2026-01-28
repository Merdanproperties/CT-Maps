"""
Database migration script to remove city column from properties table
All data should already be in municipality column
"""
import sys
from pathlib import Path
from sqlalchemy import text
from dotenv import load_dotenv

# Add parent directory to path (backend directory)
backend_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_path))

from database import engine, SessionLocal

load_dotenv()

def migrate_remove_city_column():
    """
    Remove city column from properties table
    All data should already be in municipality column
    """
    print("=" * 60)
    print("Removing city column from properties table")
    print("=" * 60)
    
    db = SessionLocal()
    
    try:
        # Check if column exists
        check_query = text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='properties' AND column_name='city'
        """)
        result = db.execute(check_query).fetchone()
        
        if not result:
            print("  ⏭️  Column 'city' does not exist, skipping...")
            return
        
        print("  ✅ Found 'city' column")
        
        # Check if index exists on city column
        print("\nChecking for index on city column...")
        index_check_query = text("""
            SELECT indexname 
            FROM pg_indexes 
            WHERE tablename='properties' 
            AND indexdef LIKE '%city%'
        """)
        index_result = db.execute(index_check_query).fetchall()
        
        if index_result:
            print(f"  Found {len(index_result)} index(es) on city column")
            for idx in index_result:
                index_name = idx[0]
                print(f"    Dropping index: {index_name}")
                try:
                    drop_index_query = text(f"DROP INDEX IF EXISTS {index_name}")
                    db.execute(drop_index_query)
                    db.commit()
                    print(f"      ✅ Dropped index: {index_name}")
                except Exception as e:
                    print(f"      ⚠️  Error dropping index {index_name}: {e}")
                    db.rollback()
        else:
            print("  No indexes found on city column")
        
        # Drop column
        print("\nDropping city column...")
        alter_query = text("ALTER TABLE properties DROP COLUMN IF EXISTS city")
        db.execute(alter_query)
        db.commit()
        print("  ✅ Dropped column 'city'")
        
        # Verify column is removed
        verify_query = text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='properties' AND column_name='city'
        """)
        verify_result = db.execute(verify_query).fetchone()
        
        if verify_result:
            print("  ⚠️  WARNING: Column still exists after drop!")
        else:
            print("  ✅ Verified: Column 'city' has been removed")
        
        print("\n" + "=" * 60)
        print("✅ Migration complete!")
        print("=" * 60)
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ Error during migration: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    migrate_remove_city_column()
