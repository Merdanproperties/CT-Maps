#!/usr/bin/env python3
"""
Analyze parcel IDs across all towns to find duplicates and check if they share the same address.
"""

import pandas as pd
import os
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple

def analyze_parcel_ids():
    """Analyze all Excel files for duplicate parcel IDs across towns."""
    
    base_dir = Path(__file__).parent / "Excel geodatabase all towns"
    
    if not base_dir.exists():
        print(f"Directory not found: {base_dir}")
        return
    
    # Dictionary to track parcel IDs: {parcel_id: [(town, address), ...]}
    parcel_id_map = defaultdict(list)
    
    # Track statistics
    total_files = 0
    total_parcels = 0
    files_processed = 0
    
    # Get all Excel files (excluding temp files starting with ~$)
    excel_files = [f for f in base_dir.glob("*.xlsx") if not f.name.startswith("~$")]
    total_files = len(excel_files)
    
    print(f"Found {total_files} Excel files to process...")
    print("-" * 80)
    
    for excel_file in sorted(excel_files):
        town_name = excel_file.stem  # Get filename without extension
        files_processed += 1
        
        try:
            print(f"[{files_processed}/{total_files}] Processing {town_name}...", end=" ")
            
            # Read the Excel file
            df = pd.read_excel(excel_file)
            
            # Check if required columns exist
            if 'Parcel_ID' not in df.columns:
                print(f"SKIPPED - No 'Parcel_ID' column")
                continue
            
            if 'Location' not in df.columns:
                print(f"SKIPPED - No 'Location' column")
                continue
            
            # Process each row
            parcels_in_file = 0
            for idx, row in df.iterrows():
                parcel_id = row.get('Parcel_ID')
                location = row.get('Location', '')
                
                # Skip if parcel_id is missing or NaN
                if pd.isna(parcel_id) or parcel_id == '' or str(parcel_id).strip() == '':
                    continue
                
                # Normalize parcel_id (convert to string, strip whitespace)
                parcel_id = str(parcel_id).strip()
                
                # Normalize location (convert to string, strip whitespace)
                location = str(location).strip() if pd.notna(location) else ''
                
                # Store the parcel ID with its town and address
                parcel_id_map[parcel_id].append((town_name, location))
                parcels_in_file += 1
                total_parcels += 1
            
            print(f"✓ {parcels_in_file:,} parcels")
            
        except Exception as e:
            print(f"ERROR: {str(e)}")
            continue
    
    print("-" * 80)
    print(f"\nTotal parcels processed: {total_parcels:,}")
    print(f"Unique parcel IDs: {len(parcel_id_map):,}")
    
    # Find duplicates (parcel IDs that appear in multiple towns)
    duplicates = {pid: towns for pid, towns in parcel_id_map.items() if len(towns) > 1}
    
    print(f"\nParcel IDs appearing in multiple towns: {len(duplicates):,}")
    
    if duplicates:
        print("\n" + "=" * 80)
        print("DUPLICATE PARCEL ID ANALYSIS")
        print("=" * 80)
        
        # Analyze address consistency
        same_address_count = 0
        different_address_count = 0
        missing_address_count = 0
        
        duplicate_details = []
        
        for parcel_id, occurrences in sorted(duplicates.items(), key=lambda x: len(x[1]), reverse=True):
            towns = [town for town, _ in occurrences]
            addresses = [addr for _, addr in occurrences]
            
            # Check if all addresses are the same
            unique_addresses = set(addr for addr in addresses if addr and addr != '')
            
            if len(unique_addresses) == 0:
                # All addresses are missing/empty
                missing_address_count += 1
                address_status = "ALL_MISSING"
            elif len(unique_addresses) == 1:
                # All addresses are the same
                same_address_count += 1
                address_status = "SAME_ADDRESS"
            else:
                # Different addresses
                different_address_count += 1
                address_status = "DIFFERENT_ADDRESSES"
            
            duplicate_details.append({
                'parcel_id': parcel_id,
                'num_towns': len(towns),
                'towns': towns,
                'addresses': addresses,
                'unique_addresses': list(unique_addresses),
                'address_status': address_status
            })
        
        # Print summary statistics
        print(f"\nSummary:")
        print(f"  - Same address across all towns: {same_address_count:,}")
        print(f"  - Different addresses: {different_address_count:,}")
        print(f"  - Missing addresses: {missing_address_count:,}")
        
        # Show examples of each type
        print("\n" + "-" * 80)
        print("EXAMPLES: Same Address (likely valid duplicates)")
        print("-" * 80)
        same_address_examples = [d for d in duplicate_details if d['address_status'] == 'SAME_ADDRESS'][:10]
        for ex in same_address_examples:
            print(f"\nParcel ID: {ex['parcel_id']}")
            print(f"  Towns ({ex['num_towns']}): {', '.join(ex['towns'])}")
            print(f"  Address: {ex['unique_addresses'][0] if ex['unique_addresses'] else 'N/A'}")
        
        print("\n" + "-" * 80)
        print("EXAMPLES: Different Addresses (likely data errors)")
        print("-" * 80)
        diff_address_examples = [d for d in duplicate_details if d['address_status'] == 'DIFFERENT_ADDRESSES'][:10]
        for ex in diff_address_examples:
            print(f"\nParcel ID: {ex['parcel_id']}")
            print(f"  Towns ({ex['num_towns']}): {', '.join(ex['towns'])}")
            print(f"  Unique addresses ({len(ex['unique_addresses'])}):")
            for addr in ex['unique_addresses']:
                print(f"    - {addr}")
        
        print("\n" + "-" * 80)
        print("EXAMPLES: Missing Addresses")
        print("-" * 80)
        missing_address_examples = [d for d in duplicate_details if d['address_status'] == 'ALL_MISSING'][:10]
        for ex in missing_address_examples:
            print(f"\nParcel ID: {ex['parcel_id']}")
            print(f"  Towns ({ex['num_towns']}): {', '.join(ex['towns'])}")
            print(f"  Address: [MISSING]")
        
        # Show most problematic duplicates (appearing in most towns)
        print("\n" + "-" * 80)
        print("TOP 20 DUPLICATES (appearing in most towns)")
        print("-" * 80)
        top_duplicates = sorted(duplicate_details, key=lambda x: x['num_towns'], reverse=True)[:20]
        for ex in top_duplicates:
            print(f"\nParcel ID: {ex['parcel_id']}")
            print(f"  Appears in {ex['num_towns']} towns: {', '.join(ex['towns'])}")
            print(f"  Status: {ex['address_status']}")
            if ex['unique_addresses']:
                print(f"  Addresses: {', '.join(ex['unique_addresses'][:3])}")
                if len(ex['unique_addresses']) > 3:
                    print(f"    ... and {len(ex['unique_addresses']) - 3} more")
        
        # Export detailed report to CSV
        output_file = Path(__file__).parent / "duplicate_parcel_ids_report.csv"
        export_df = pd.DataFrame([
            {
                'parcel_id': d['parcel_id'],
                'num_towns': d['num_towns'],
                'towns': '; '.join(d['towns']),
                'address_status': d['address_status'],
                'unique_addresses': '; '.join(d['unique_addresses']) if d['unique_addresses'] else '[MISSING]',
                'all_addresses': '; '.join(d['addresses']) if d['addresses'] else '[MISSING]'
            }
            for d in duplicate_details
        ])
        export_df.to_csv(output_file, index=False)
        print(f"\n\nDetailed report exported to: {output_file}")
        
    else:
        print("\n✓ No duplicate parcel IDs found across towns!")
    
    return duplicates

if __name__ == "__main__":
    analyze_parcel_ids()
