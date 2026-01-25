"""
Database migration script to add new CAMA fields to properties table
Adds fields for tax information, building exterior/interior details
"""
import sys
from pathlib import Path
from sqlalchemy import text
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from database import engine, SessionLocal

load_dotenv()

def migrate_add_cama_fields():
    """
    Add new columns to properties table for CAMA data
    All new columns are nullable to handle existing data
    """
    print("=" * 60)
    print("Adding CAMA fields to properties table")
    print("=" * 60)
    
    db = SessionLocal()
    
    try:
        # List of new columns to add
        new_columns = [
            # Property characteristics
            ("stories", "INTEGER"),
            ("total_rooms", "INTEGER"),
            
            # Tax Information
            ("tax_amount", "DOUBLE PRECISION"),
            ("tax_year", "INTEGER"),
            ("tax_exemptions", "VARCHAR"),
            
            # Building Exterior Details
            ("exterior_walls", "VARCHAR"),
            ("roof_type", "VARCHAR"),
            ("roof_material", "VARCHAR"),
            ("foundation_type", "VARCHAR"),
            ("exterior_finish", "VARCHAR"),
            ("garage_type", "VARCHAR"),
            ("garage_spaces", "INTEGER"),
            
            # Building Interior Details
            ("interior_finish", "VARCHAR"),
            ("heating_type", "VARCHAR"),
            ("cooling_type", "VARCHAR"),
            ("fireplace_count", "INTEGER"),
        ]
        
        added_count = 0
        skipped_count = 0
        
        for column_name, column_type in new_columns:
            try:
                # Check if column already exists
                check_query = text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='properties' AND column_name=:col_name
                """)
                result = db.execute(check_query, {"col_name": column_name}).fetchone()
                
                if result:
                    print(f"  ⏭️  Column '{column_name}' already exists, skipping...")
                    skipped_count += 1
                    continue
                
                # Add column
                alter_query = text(f"ALTER TABLE properties ADD COLUMN {column_name} {column_type}")
                db.execute(alter_query)
                db.commit()
                print(f"  ✅ Added column '{column_name}' ({column_type})")
                added_count += 1
                
            except Exception as e:
                db.rollback()
                print(f"  ❌ Error adding column '{column_name}': {e}")
                raise
        
        print("\n" + "=" * 60)
        print("Migration Summary:")
        print(f"  ✅ Added: {added_count} columns")
        print(f"  ⏭️  Skipped: {skipped_count} columns (already exist)")
        print("=" * 60)
        
        # Create indexes for commonly searched fields
        print("\nCreating indexes for new searchable fields...")
        indexes = [
            ("idx_property_stories", "stories"),
            ("idx_property_heating_type", "heating_type"),
            ("idx_property_cooling_type", "cooling_type"),
        ]
        
        for index_name, column_name in indexes:
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
                    continue
                
                # Create index
                create_index = text(f"CREATE INDEX {index_name} ON properties ({column_name})")
                db.execute(create_index)
                db.commit()
                print(f"  ✅ Created index '{index_name}' on '{column_name}'")
                
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
    migrate_add_cama_fields()
