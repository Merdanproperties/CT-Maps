"""
Export Unmatched Properties to Excel
Generates Excel files for each town with properties that don't have CAMA data
"""
import sys
from pathlib import Path
from typing import Dict, List
import pandas as pd
from datetime import datetime
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from database import SessionLocal
from models import Property
from scripts.data_import.cama_verification import verify_cama_data, get_file_paths, find_excel_match_for_property
from scripts.data_import.automated_cama_verification import get_all_municipalities
from scripts.data_import.import_bridgeport_cama_2025 import (
    read_cleaned_excel,
    read_raw_csv,
    match_and_combine,
    normalize_address
)

def export_unmatched_properties_to_excel(municipality: str, db: Session, output_dir: str = None) -> str:
    """
    Export unmatched properties to Excel file
    Returns path to created Excel file
    """
    print(f"\n{'='*80}")
    print(f"Exporting Unmatched Properties for {municipality}")
    print(f"{'='*80}")
    
    # Run verification to get unmatched properties
    print("\nStep 1: Running verification to identify unmatched properties...")
    try:
        result = verify_cama_data(municipality, db)
    except ValueError:
        # Verification failed but we still want unmatched list
        # Re-run with no-raise mode by manually finding unmatched
        print("  Verification found mismatches, but extracting unmatched list...")
        
        # Get file paths
        file_paths = get_file_paths(municipality)
        cleaned_file = file_paths['cleaned_excel']
        csv_file = file_paths['csv']
        
        if not Path(cleaned_file).exists():
            print(f"  ⚠️  Cleaned Excel file not found: {cleaned_file}")
            return None
        
        # Load Excel data
        cleaned_df = read_cleaned_excel(cleaned_file)
        raw_lookup = {}
        if Path(csv_file).exists():
            _, raw_lookup = read_raw_csv(csv_file)
        combined_records = match_and_combine(cleaned_df, raw_lookup)
        
        # Build lookups
        parcel_lookup = {}
        address_lookup = {}
        for idx, record in enumerate(combined_records):
            parcel_id = record.get('parcel_id')
            if not parcel_id and 'raw_Parcel ID' in record:
                parcel_id = str(record['raw_Parcel ID']).strip()
            if parcel_id and parcel_id != 'nan' and parcel_id:
                parcel_lookup[str(parcel_id).strip()] = idx
            
            address = record.get('Property Address')
            if address:
                norm_addr = normalize_address(address)
                if norm_addr:
                    if norm_addr not in address_lookup:
                        address_lookup[norm_addr] = []
                    address_lookup[norm_addr].append(record)
        
        # Find unmatched
        properties = db.query(Property).filter(
            Property.municipality.ilike(f"%{municipality}%")
        ).all()
        
        unmatched = []
        for prop in properties:
            excel_match = find_excel_match_for_property(prop, combined_records, parcel_lookup, address_lookup)
            if not excel_match:
                unmatched.append({
                    'property_id': prop.id,
                    'parcel_id': prop.parcel_id,
                    'address': prop.address
                })
        
        result = {
            'unmatched_list': unmatched
        }
    
    unmatched_list = result.get('unmatched_list', [])
    
    if not unmatched_list:
        print(f"\n✅ No unmatched properties found for {municipality}")
        return None
    
    print(f"\nStep 2: Loading full property details for {len(unmatched_list):,} unmatched properties...")
    
    # Get full property details from database
    property_ids = [item['property_id'] for item in unmatched_list]
    properties = db.query(Property).filter(Property.id.in_(property_ids)).all()
    
    # Create property lookup
    prop_dict = {p.id: p for p in properties}
    
    # Build Excel data
    excel_data = []
    for item in unmatched_list:
        prop = prop_dict.get(item['property_id'])
        if prop:
            excel_data.append({
                'Property ID': prop.id,
                'Parcel ID': prop.parcel_id or '',
                'Address': prop.address or '',
                'Municipality': prop.municipality or '',
                'Zip Code': prop.zip_code or '',
                'Owner Name': prop.owner_name or '',
                'Owner Address': prop.owner_address or '',
                'Owner City': prop.owner_city or '',
                'Owner State': prop.owner_state or '',
                'Assessed Value': prop.assessed_value if prop.assessed_value else '',
                'Land Value': prop.land_value if prop.land_value else '',
                'Building Value': prop.building_value if prop.building_value else '',
                'Property Type': prop.property_type or '',
                'Land Use': prop.land_use or '',
                'Building Area (sqft)': prop.building_area_sqft if prop.building_area_sqft else '',
                'Lot Size (sqft)': prop.lot_size_sqft if prop.lot_size_sqft else '',
                'Year Built': prop.year_built if prop.year_built else '',
                'Last Sale Date': prop.last_sale_date.strftime('%Y-%m-%d') if prop.last_sale_date else '',
                'Last Sale Price': prop.last_sale_price if prop.last_sale_price else '',
                'Has Geometry': 'Yes' if prop.geometry else 'No',
                'Data Source': prop.data_source or '',
                'Last Updated': prop.last_updated.strftime('%Y-%m-%d') if prop.last_updated else ''
            })
    
    # Create DataFrame
    df = pd.DataFrame(excel_data)
    
    # Sort by address for easier review
    df = df.sort_values(by=['Address', 'Parcel ID'])
    
    # Create output directory (default to workspace root Analysis scripts folder)
    if output_dir is None:
        # Get workspace root (3 levels up from this script)
        workspace_root = Path(__file__).parent.parent.parent.parent
        output_path = workspace_root / "Analysis scripts"
    else:
        output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Generate filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{municipality}_Unmatched_Properties_{timestamp}.xlsx"
    filepath = output_path / filename
    
    # Export to Excel
    print(f"\nStep 3: Exporting to Excel...")
    with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Unmatched Properties', index=False)
        
        # Auto-adjust column widths
        worksheet = writer.sheets['Unmatched Properties']
        for idx, col in enumerate(df.columns):
            max_length = max(
                df[col].astype(str).map(len).max(),
                len(str(col))
            )
            # Excel column letters: A=65, B=66, etc.
            col_letter = chr(65 + idx) if idx < 26 else chr(65 + idx // 26 - 1) + chr(65 + idx % 26)
            worksheet.column_dimensions[col_letter].width = min(max_length + 2, 50)
    
    print(f"  ✅ Exported {len(excel_data):,} unmatched properties to:")
    print(f"     {filepath}")
    
    return str(filepath)

def export_all_towns_unmatched():
    """
    Export unmatched properties for all towns
    """
    print("\n" + "=" * 80)
    print("EXPORTING UNMATCHED PROPERTIES FOR ALL TOWNS")
    print("=" * 80)
    
    db = SessionLocal()
    
    try:
        municipalities = get_all_municipalities(db)
        
        if not municipalities:
            print("\n⚠️  No municipalities found in database")
            return
        
        print(f"\nFound {len(municipalities):,} municipalities:")
        for m in municipalities:
            print(f"  - {m}")
        
        exported_files = []
        
        for municipality in municipalities:
            try:
                filepath = export_unmatched_properties_to_excel(municipality, db)
                if filepath:
                    exported_files.append((municipality, filepath))
            except Exception as e:
                print(f"\n❌ Error exporting {municipality}: {str(e)}")
                import traceback
                traceback.print_exc()
        
        # Summary
        print("\n" + "=" * 80)
        print("EXPORT SUMMARY")
        print("=" * 80)
        print(f"\n  Total Towns: {len(municipalities):,}")
        print(f"  ✅ Exported: {len(exported_files):,}")
        
        if exported_files:
            print(f"\n  Exported Files:")
            for municipality, filepath in exported_files:
                print(f"    {municipality}: {filepath}")
        
    finally:
        db.close()

def main():
    """Main function for command-line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Export Unmatched Properties to Excel')
    parser.add_argument('--municipality', type=str, help='Export specific municipality')
    parser.add_argument('--all', action='store_true', help='Export all towns')
    parser.add_argument('--output-dir', type=str, default=None, help='Output directory for Excel files (default: workspace root/Analysis scripts)')
    
    args = parser.parse_args()
    
    if args.all:
        export_all_towns_unmatched()
    elif args.municipality:
        db = SessionLocal()
        try:
            export_unmatched_properties_to_excel(args.municipality, db, args.output_dir)
        finally:
            db.close()
    else:
        # Default: export all towns
        export_all_towns_unmatched()

if __name__ == "__main__":
    main()
