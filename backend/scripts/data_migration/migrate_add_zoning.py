"""
Database migration script to add zoning column to properties table
"""
import sys
from pathlib import Path
from sqlalchemy import text
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from database import engine, SessionLocal

load_dotenv()

def migrate_add_zoning():
    """
    Add zoning column to properties table
    Column is nullable to handle existing data
    """
    print("=" * 60)
    print("Adding zoning column to properties table")
    print("=" * 60)
    
    db = SessionLocal()
    
    try:
        # Check if column already exists
        check_query = text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='properties' AND column_name='zoning'
        """)
        result = db.execute(check_query).fetchone()
        
        if result:
            print("  ⏭️  Column 'zoning' already exists, skipping...")
        else:
            # Add column
            alter_query = text("ALTER TABLE properties ADD COLUMN zoning VARCHAR")
            db.execute(alter_query)
            db.commit()
            print("  ✅ Added column 'zoning' (VARCHAR)")
        
        # Create index for zoning
        print("\nCreating index for zoning column...")
        index_name = "idx_property_zoning"
        
        try:
            # Check if index already exists
            check_index = text("""
                SELECT indexname 
                FROM pg_indexes 
                WHERE tablename='properties' AND indexname=:idx_name
            """)
            result = db.execute(check_index, {"idx_name": index_name}).fetchone()
            
            if result:
                print(f"  ⏭️  Index '{index_name}' already exists, skipping...")
            else:
                # Create index
                create_index = text(f"CREATE INDEX {index_name} ON properties (zoning)")
                db.execute(create_index)
                db.commit()
                print(f"  ✅ Created index '{index_name}' on 'zoning'")
                
        except Exception as e:
            db.rollback()
            print(f"  ⚠️  Could not create index '{index_name}': {e}")
            # Don't fail migration if index creation fails
        
        print("\n✅ Migration completed successfully!")
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ Migration failed: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    migrate_add_zoning()
