"""
Batch import script for all remaining towns with location data
Excludes: Torrington, Bridgeport, Middletown (already imported)
"""
import sys
import time
import json
import os
import argparse
from pathlib import Path
from datetime import datetime
import pandas as pd
from sqlalchemy import func

# Backend is 4 levels up (script is in backend/scripts/data_import/134_towns/)
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
# Same-dir import (folder name starts with digit so not useable as package in import)
sys.path.insert(0, str(Path(__file__).parent))

from import_town_optimized import import_town_optimized
from database import SessionLocal
from models import Property
from sqlalchemy import text

# Read list of towns to import
TOWNS_FILE = Path(__file__).parent / "towns_to_import.txt"

def main():
    print("=" * 80)
    print("BATCH IMPORT: All Remaining Towns with Location Data")
    print("=" * 80)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    parser = argparse.ArgumentParser(description="Batch import towns")
    parser.add_argument("--start-batch", type=int, default=1, help="Start from batch N (1-based). E.g. 3 = skip batches 1-2.")
    args = parser.parse_args()
    start_batch = max(1, args.start_batch)
    if start_batch > 1:
        print(f"▶ Starting from BATCH {start_batch} (skipping earlier batches)")
    print()
    
    # Read towns list
    if not TOWNS_FILE.exists():
        print(f"❌ Towns list not found: {TOWNS_FILE}")
        print("   Please run the analysis script first to generate the list.")
        return
    
    with open(TOWNS_FILE, 'r') as f:
        all_towns = [line.strip() for line in f if line.strip()]
    BATCH_SIZE = 10
    total_batches_full = (len(all_towns) + BATCH_SIZE - 1) // BATCH_SIZE
    if start_batch > total_batches_full:
        print(f"❌ --start-batch {start_batch} invalid (max is {total_batches_full})")
        return
    skip_towns = (start_batch - 1) * BATCH_SIZE
    towns = all_towns[skip_towns:] if skip_towns > 0 else all_towns
    total_towns_display = len(all_towns)
    if skip_towns > 0:
        print(f"Skipping first {skip_towns} towns (batches 1–{start_batch - 1}). Remaining: {len(towns)} towns.")
    total_batches = (len(towns) + BATCH_SIZE - 1) // BATCH_SIZE
    print(f"\nTowns to process: {len(towns)} | Batches: {total_batches} | Est. time: ~{total_batches * 8} min\n")
    
    # Track results
    results = {
        'success': [],
        'failed': [],
        'skipped': []
    }
    
    start_time = time.time()
    
    # Track counts for each town
    town_tracking = []
    
    # Process in batches of 10
    BATCH_SIZE = 10
    total_batches = (len(towns) + BATCH_SIZE - 1) // BATCH_SIZE
    
    for batch_num in range(total_batches):
        batch_start_idx = batch_num * BATCH_SIZE
        batch_end_idx = min(batch_start_idx + BATCH_SIZE, len(towns))
        batch_towns = towns[batch_start_idx:batch_end_idx]
        
        batch_display = batch_num + start_batch
        total_batches_display = total_batches_full
        # Global 1-based town numbers: must match "TOWN X/132" for first and last town in this batch
        first_town_num = skip_towns + batch_start_idx + 1
        last_town_num = skip_towns + min(batch_start_idx + BATCH_SIZE, len(towns))
        print("\n" + "=" * 80)
        print(f"BATCH {batch_display}/{total_batches_display}: Processing towns {first_town_num}-{last_town_num}")
        print("=" * 80)
        print(f"Towns in this batch: {', '.join(batch_towns)}")
        print()
        
        batch_start_time = time.time()
        
        for local_idx, town in enumerate(batch_towns):
            i = batch_start_idx + local_idx + 1
            i_display = skip_towns + i  # Global 1-based town number (matches "Processing towns X-Y" above)
            town_start = time.time()
            print("\n" + "=" * 80)
            print(f"TOWN {i_display}/{total_towns_display}: {town.upper()}")
            print("=" * 80)
            
            # Get count BEFORE import
            db = SessionLocal()
            try:
                count_before = db.query(Property).filter(func.lower(Property.municipality) == town.lower()).count()
            except Exception as e:
                count_before = 0
                print(f"  ⚠️  Error getting count before: {e}")
            finally:
                db.close()
            
            print(f"  📊 Count BEFORE import: {count_before:,}")
            
            try:
                result = import_town_optimized(
                    municipality=town,
                    dry_run=False
                )
                
                # Get count AFTER import (wait for DB to release connection from import)
                sys.stdout.flush()
                time.sleep(2)
                print(f"  Getting count after import...", flush=True)
                db = SessionLocal()
                try:
                    count_after = db.query(Property).filter(func.lower(Property.municipality) == town.lower()).count()
                except Exception as e:
                    count_after = count_before
                    print(f"  ⚠️  Error getting count after: {e}")
                finally:
                    db.close()
                
                # Calculate expected count
                expected_count = count_before + result['inserted'] - result.get('updated', 0)
                count_change = count_after - count_before
                count_stable = (count_after == result.get('final_db_count', count_after))
                
                town_time = time.time() - town_start
                elapsed_total = time.time() - start_time
                avg_time_per_town = elapsed_total / i
                remaining_towns = len(towns) - i
                estimated_remaining = avg_time_per_town * remaining_towns
                
                print(f"\n✅ {town} completed in {town_time:.1f}s")
                print(f"   Inserted: {result['inserted']:,} | Updated: {result['updated']:,}")
                print(f"   📊 Count BEFORE: {count_before:,} | AFTER: {count_after:,} | Change: {count_change:+,}")
                print(f"   Expected final: {result.get('final_db_count', 'N/A')}")
                
                # Check for count decrease issue
                if count_after < count_before and result['inserted'] > 0:
                    print(f"   ⚠️  WARNING: Count DECREASED after import! ({count_before:,} → {count_after:,})")
                    town_tracking.append({
                        'town': town,
                        'count_before': count_before,
                        'count_after': count_after,
                        'count_decreased': True,
                        'inserted': result['inserted'],
                        'updated': result['updated']
                    })
                elif not count_stable and result.get('final_db_count'):
                    print(f"   ⚠️  NOTE: Count mismatch with reported final count")
                    town_tracking.append({
                        'town': town,
                        'count_before': count_before,
                        'count_after': count_after,
                        'reported_final': result.get('final_db_count'),
                        'count_mismatch': True
                    })
                else:
                    town_tracking.append({
                        'town': town,
                        'count_before': count_before,
                        'count_after': count_after,
                        'count_stable': True
                    })
                
                print(f"   Progress: {i_display}/{total_towns_display} ({i_display/total_towns_display*100:.1f}%)")
                print(f"   Elapsed: {elapsed_total/60:.1f} min | Est. remaining: {estimated_remaining/60:.1f} min")
                
                results['success'].append({
                    'town': town,
                    'inserted': result['inserted'],
                    'updated': result['updated'],
                    'matched': result['matched'],
                    'count_before': count_before,
                    'count_after': count_after,
                    'time': town_time
                })
            
            except FileNotFoundError as e:
                print(f"\n⚠️  {town} skipped: {str(e)}")
                results['skipped'].append({'town': town, 'reason': str(e)})
            
            except Exception as e:
                print(f"\n❌ {town} failed: {str(e)}")
                results['failed'].append({'town': town, 'error': str(e)})
            # Continue with next town
            continue
        
        # Batch complete - show summary and wait for approval
        batch_time = time.time() - batch_start_time
        batch_success = [r for r in results['success'] if r['town'] in batch_towns]
        batch_failed = [r for r in results['failed'] if r['town'] in batch_towns]
        batch_skipped = [r for r in results['skipped'] if r['town'] in batch_towns]
        
        print("\n" + "=" * 80)
        print(f"BATCH {batch_display}/{total_batches_display} COMPLETE")
        print("=" * 80)
        print(f"Batch time: {batch_time/60:.1f} minutes")
        print(f"✅ Success: {len(batch_success)}")
        print(f"❌ Failed: {len(batch_failed)}")
        if batch_skipped:
            print(f"⏭️  Skipped: {len(batch_skipped)}")
        
        # Check for count decreases in this batch (only among towns that were processed)
        batch_count_decreases = [t for t in town_tracking[-len(batch_success):] if t.get('count_decreased')]
        if batch_count_decreases:
            print(f"\n⚠️  COUNT DECREASES DETECTED IN THIS BATCH:")
            for t in batch_count_decreases:
                print(f"  {t['town']}: {t['count_before']:,} → {t['count_after']:,}")
        
        print(f"\nTowns processed in this batch:")
        for town_result in batch_success:
            print(f"  ✅ {town_result['town']}: {town_result['count_before']:,} → {town_result['count_after']:,} "
                  f"(+{town_result['count_after'] - town_result['count_before']:,})")
        
        if batch_skipped:
            print(f"\nSkipped towns:")
            for s in batch_skipped:
                reason = (s.get('reason') or '')[:80]
                print(f"  ⏭️  {s['town']}: {reason}")
        
        if batch_failed:
            print(f"\nFailed towns:")
            for f in batch_failed:
                print(f"  ❌ {f['town']}: {f['error'][:100]}")
        
        sys.stdout.flush()  # So tail -f shows batch summary immediately
        
        # Wait for approval before next batch
        if batch_num < total_batches - 1:  # Don't ask after last batch
            approval_file = Path(__file__).parent / "APPROVE_NEXT_BATCH.txt"
            stop_file = Path(__file__).parent / "STOP_IMPORT.txt"
            
            # Clean up any existing approval files
            approval_file.unlink(missing_ok=True)
            stop_file.unlink(missing_ok=True)
            
            print("\n" + "=" * 80)
            print("⏸️  BATCH COMPLETE - WAITING FOR APPROVAL")
            print("=" * 80)
            print(f"Next batch will process: {', '.join(towns[batch_end_idx:batch_end_idx + BATCH_SIZE])}")
            print(f"\n📝 TO APPROVE: Create this file: {approval_file.name}")
            print(f"📝 TO STOP: Create this file: {stop_file.name}")
            print("\nWaiting for approval file...")
            print("=" * 80)
            sys.stdout.flush()  # So tail -f shows approval message immediately
            
            # Wait for approval file
            max_wait = 3600  # Wait up to 1 hour
            wait_time = 0
            check_interval = 2  # Check every 2 seconds
            
            while wait_time < max_wait:
                if stop_file.exists():
                    print(f"\n⚠️  Stop file detected - import stopped by user")
                    stop_file.unlink(missing_ok=True)
                    break
                
                if approval_file.exists():
                    print(f"\n✅ Approval file detected - continuing to next batch...\n")
                    approval_file.unlink(missing_ok=True)
                    break
                
                time.sleep(check_interval)
                wait_time += check_interval
                
                # Show progress every 10 seconds
                if wait_time % 10 == 0:
                    print(f"   Still waiting... ({wait_time}s elapsed)")
            
            if stop_file.exists() or wait_time >= max_wait:
                if wait_time >= max_wait:
                    print(f"\n⚠️  Timeout reached - stopping import")
                break
    
    # Final summary
    total_time = time.time() - start_time
    print("\n" + "=" * 80)
    print("BATCH IMPORT COMPLETE")
    print("=" * 80)
    print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total time: {total_time/60:.1f} minutes ({total_time/3600:.2f} hours)")
    print(f"\nResults:")
    print(f"  ✅ Success: {len(results['success'])}")
    print(f"  ❌ Failed: {len(results['failed'])}")
    print(f"  ⚠️  Skipped: {len(results['skipped'])}")
    
    if results['success']:
        total_inserted = sum(r['inserted'] for r in results['success'])
        total_updated = sum(r['updated'] for r in results['success'])
        print(f"\n  Total inserted: {total_inserted:,}")
        print(f"  Total updated: {total_updated:,}")
    
    if results['failed']:
        print(f"\nFailed towns:")
        for f in results['failed']:
            print(f"  - {f['town']}: {f['error']}")
    
    if results['skipped']:
        print(f"\nSkipped towns:")
        for s in results['skipped']:
            print(f"  - {s['town']}: {s['reason']}")
    
    # Report count tracking issues
    if town_tracking:
        count_decreased = [t for t in town_tracking if t.get('count_decreased')]
        count_mismatch = [t for t in town_tracking if t.get('count_mismatch')]
        
        if count_decreased:
            print(f"\n" + "=" * 80)
            print("⚠️  COUNT DECREASE DETECTED")
            print("=" * 80)
            for t in count_decreased:
                print(f"  {t['town']}: {t['count_before']:,} → {t['count_after']:,} "
                      f"(inserted {t['inserted']:,}, updated {t['updated']:,})")
        
        if count_mismatch:
            print(f"\n" + "=" * 80)
            print("⚠️  COUNT MISMATCH DETECTED")
            print("=" * 80)
            for t in count_mismatch:
                print(f"  {t['town']}: Actual={t['count_after']:,}, Reported={t.get('reported_final', 'N/A')}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Import interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Batch import failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
