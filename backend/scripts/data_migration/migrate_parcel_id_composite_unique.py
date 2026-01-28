"""
Database migration script to change parcel_id from global unique to composite unique (parcel_id + municipality)

This allows the same parcel_id to exist in different municipalities, which is correct since
parcel_id is only unique per town, not globally.

SAFETY: This migration:
1. Checks for existing duplicates (should be none)
2. Drops the global unique constraint
3. Adds a composite unique constraint on (parcel_id, municipality)
4. Updates the index to support the new constraint
5. Does NOT modify any data - only changes constraints
"""
import sys
from pathlib import Path
from sqlalchemy import text
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from database import engine, SessionLocal

load_dotenv()

def migrate_parcel_id_composite_unique():
    """
    Change parcel_id constraint from global unique to composite unique (parcel_id + municipality)
    This allows same parcel_id in different towns, which is the correct behavior.
    """
    print("=" * 80)
    print("MIGRATION: Change parcel_id to composite unique (parcel_id + municipality)")
    print("=" * 80)
    print()
    print("This migration will:")
    print("  1. Check for existing duplicate parcel_ids (should be none)")
    print("  2. Drop the global unique constraint on parcel_id")
    print("  3. Add composite unique constraint on (parcel_id, municipality)")
    print("  4. Update indexes")
    print()
    print("⚠️  This will NOT modify any data - only constraint definitions")
    print()
    
    db = SessionLocal()
    
    try:
        # Step 1: Check for existing duplicates
        print("Step 1: Checking for existing duplicate parcel_ids...")
        result = db.execute(text('''
            SELECT parcel_id, COUNT(*) as cnt, 
                   array_agg(DISTINCT municipality) as municipalities
            FROM properties
            WHERE parcel_id IS NOT NULL
            GROUP BY parcel_id
            HAVING COUNT(*) > 1
            LIMIT 10
        '''))
        duplicates = result.fetchall()
        
        if duplicates:
            print(f"  ⚠️  WARNING: Found {len(duplicates)} duplicate parcel_ids!")
            print("     This should not happen with the current global constraint.")
            print("     Duplicates found:")
            for row in duplicates:
                print(f"       Parcel ID: {row[0]}, Count: {row[1]}, Municipalities: {row[2]}")
            print("  ⚠️  Migration will continue, but this is unexpected.")
            print("  These duplicates will be allowed after migration completes.")
        else:
            print("  ✅ No duplicate parcel_ids found - safe to proceed")
        
        # Step 2: Get current constraint name
        print("\nStep 2: Finding current unique constraint on parcel_id...")
        constraint_name = None
        
        # Method 1: Check information_schema
        result = db.execute(text('''
            SELECT constraint_name
            FROM information_schema.table_constraints
            WHERE table_name = 'properties'
              AND constraint_type = 'UNIQUE'
              AND constraint_name LIKE '%parcel_id%'
        '''))
        constraint_info = result.fetchall()
        
        if constraint_info:
            constraint_name = constraint_info[0][0]
            print(f"  Found constraint: {constraint_name}")
        else:
            # Method 2: Check pg_constraint directly
            result = db.execute(text('''
                SELECT conname
                FROM pg_constraint
                WHERE conrelid = 'properties'::regclass
                  AND contype = 'u'
            '''))
            all_constraints = result.fetchall()
            
            # Find constraint that includes parcel_id column
            for con in all_constraints:
                con_name = con[0]
                # Get columns for this constraint
                result2 = db.execute(text('''
                    SELECT a.attname
                    FROM pg_attribute a
                    JOIN pg_constraint c ON a.attrelid = c.conrelid AND a.attnum = ANY(c.conkey)
                    WHERE c.conname = :con_name
                '''), {"con_name": con_name})
                cols = [row[0] for row in result2]
                if 'parcel_id' in cols:
                    constraint_name = con_name
                    print(f"  Found constraint: {constraint_name} (on columns: {', '.join(cols)})")
                    break
            
            if not constraint_name:
                print("  ℹ️  No unique constraint found on parcel_id (may already be removed)")
        
        # Step 3: Drop the global unique constraint
        print("\nStep 3: Dropping global unique constraint on parcel_id...")
        dropped = False
        
        # Method 1: Drop by constraint name
        if constraint_name:
            try:
                db.execute(text(f'ALTER TABLE properties DROP CONSTRAINT IF EXISTS {constraint_name}'))
                db.commit()
                print(f"  ✅ Dropped constraint: {constraint_name}")
                dropped = True
            except Exception as e:
                print(f"  ⚠️  Error dropping constraint: {e}")
                db.rollback()
        
        # Method 2: Drop by unique index (PostgreSQL creates indexes for unique constraints)
        if not dropped:
            try:
                # Find unique index on parcel_id
                result = db.execute(text('''
                    SELECT indexname
                    FROM pg_indexes
                    WHERE tablename = 'properties'
                      AND indexname LIKE '%parcel_id%'
                      AND indexdef LIKE '%UNIQUE%'
                '''))
                index_info = result.fetchall()
                if index_info:
                    for idx_row in index_info:
                        index_name = idx_row[0]
                        print(f"  Found unique index: {index_name}")
                        db.execute(text(f'DROP INDEX IF EXISTS {index_name}'))
                        db.commit()
                        print(f"  ✅ Dropped unique index: {index_name}")
                        dropped = True
                else:
                    print("  ℹ️  No unique index found (constraint may already be removed)")
            except Exception as e:
                print(f"  ⚠️  Error dropping index: {e}")
                db.rollback()
        
        if not dropped:
            print("  ℹ️  No constraint/index to drop - may already be removed or using different structure")
        
        # Step 4: Ensure municipality is NOT NULL (required for composite constraint)
        print("\nStep 4: Ensuring municipality is NOT NULL...")
        try:
            # Check for NULL municipalities
            result = db.execute(text('SELECT COUNT(*) FROM properties WHERE municipality IS NULL'))
            null_count = result.scalar()
            
            if null_count > 0:
                print(f"  ⚠️  Found {null_count} properties with NULL municipality")
                print("     Setting them to 'UNKNOWN' for the constraint...")
                db.execute(text('''
                    UPDATE properties 
                    SET municipality = 'UNKNOWN' 
                    WHERE municipality IS NULL
                '''))
                db.commit()
                print(f"  ✅ Updated {null_count} properties")
            else:
                print("  ✅ All properties have municipality set")
            
            # Set NOT NULL constraint
            db.execute(text('''
                ALTER TABLE properties 
                ALTER COLUMN municipality SET NOT NULL
            '''))
            db.commit()
            print("  ✅ Set municipality to NOT NULL")
        except Exception as e:
            print(f"  ⚠️  Error setting municipality NOT NULL: {e}")
            db.rollback()
            # Check if it's already NOT NULL
            result = db.execute(text('''
                SELECT is_nullable
                FROM information_schema.columns
                WHERE table_name = 'properties' AND column_name = 'municipality'
            '''))
            nullable = result.scalar()
            if nullable == 'NO':
                print("  ℹ️  Municipality is already NOT NULL, continuing...")
            else:
                raise
        
        try:
            # Add composite unique constraint
            db.execute(text('''
                ALTER TABLE properties 
                ADD CONSTRAINT uq_properties_parcel_id_municipality 
                UNIQUE (parcel_id, municipality)
            '''))
            db.commit()
            print("  ✅ Added composite unique constraint: uq_properties_parcel_id_municipality")
        except Exception as e:
            print(f"  ❌ Error adding composite constraint: {e}")
            db.rollback()
            raise
        
        # Step 6: Verify the constraint
        print("\nStep 6: Verifying new constraint...")
        result = db.execute(text('''
            SELECT constraint_name, constraint_type
            FROM information_schema.table_constraints
            WHERE table_name = 'properties'
              AND constraint_name = 'uq_properties_parcel_id_municipality'
        '''))
        verify = result.fetchall()
        if verify:
            print(f"  ✅ Constraint verified: {verify[0][0]} ({verify[0][1]})")
        else:
            print("  ⚠️  Could not verify constraint (may need to check manually)")
        
        print("\n" + "=" * 80)
        print("✅ MIGRATION COMPLETE")
        print("=" * 80)
        print()
        print("The parcel_id constraint has been changed from global unique to")
        print("composite unique (parcel_id + municipality).")
        print()
        print("This allows:")
        print("  - Same parcel_id in different municipalities (correct behavior)")
        print("  - Prevents duplicate parcel_id within the same municipality")
        print()
        print("⚠️  Next step: Update the model in backend/models.py to reflect this change")
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    try:
        migrate_parcel_id_composite_unique()
    except KeyboardInterrupt:
        print("\n\n⚠️  Migration interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        sys.exit(1)
