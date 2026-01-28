"""
LLC Analysis by Town

Identifies properties owned by LLCs and other business entities,
providing breakdown by town showing LLC vs non-LLC ownership.

Output: Excel file with LLC analysis per town
"""
import sys
from pathlib import Path
import pandas as pd
from typing import Optional, Dict
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.analysis.analysis_utils import (
    get_database_session,
    load_properties_from_db,
    export_to_excel,
    create_summary_sheet,
    format_currency,
    calculate_percentage,
    detect_llc
)


def analyze_llc_ownership(
    municipality: Optional[str] = None
) -> Dict[str, pd.DataFrame]:
    """
    Analyze LLC vs non-LLC property ownership
    
    Args:
        municipality: Optional town/municipality to filter by
        
    Returns:
        Dictionary of {sheet_name: DataFrame} for Excel export
    """
    print("=" * 80)
    print("LLC OWNERSHIP ANALYSIS")
    print("=" * 80)
    
    db = get_database_session()
    
    try:
        # Load properties from database
        print(f"\nLoading properties from database...")
        if municipality:
            print(f"  Filtering by municipality: {municipality}")
        
        df = load_properties_from_db(municipality=municipality, db_session=db)
        
        if len(df) == 0:
            print("  ⚠️  No properties found")
            return {}
        
        print(f"  Loaded {len(df):,} properties")
        
        # Filter out properties without owner name
        df = df[
            df['owner_name'].notna() & 
            (df['owner_name'] != '')
        ].copy()
        
        print(f"  Properties with owner name: {len(df):,}")
        
        if len(df) == 0:
            print("  ⚠️  No properties with owner name found")
            return {}
        
        # Detect LLC status
        print("\nDetecting LLC/business entities...")
        df['is_llc'] = df['owner_name'].apply(detect_llc)
        
        llc_count = df['is_llc'].sum()
        non_llc_count = (~df['is_llc']).sum()
        
        print(f"  LLC/Business entities: {llc_count:,}")
        print(f"  Non-LLC owners: {non_llc_count:,}")
        
        # If municipality specified, create single sheet
        if municipality:
            # Create breakdown
            llc_props = df[df['is_llc']].copy()
            non_llc_props = df[~df['is_llc']].copy()
            
            total_props = len(df)
            llc_pct = calculate_percentage(llc_count, total_props)
            non_llc_pct = calculate_percentage(non_llc_count, total_props)
            
            # Create summary DataFrame
            summary_data = {
                'Category': ['LLC/Business Entities', 'Non-LLC Owners', 'Total'],
                'Property Count': [llc_count, non_llc_count, total_props],
                'Percentage': [
                    f"{llc_pct:.2f}%",
                    f"{non_llc_pct:.2f}%",
                    "100.00%"
                ],
                'Total Assessed Value': [
                    format_currency(llc_props['assessed_value'].sum()),
                    format_currency(non_llc_props['assessed_value'].sum()),
                    format_currency(df['assessed_value'].sum())
                ],
                'Total Land Value': [
                    format_currency(llc_props['land_value'].sum()),
                    format_currency(non_llc_props['land_value'].sum()),
                    format_currency(df['land_value'].sum())
                ],
                'Total Building Value': [
                    format_currency(llc_props['building_value'].sum()),
                    format_currency(non_llc_props['building_value'].sum()),
                    format_currency(df['building_value'].sum())
                ]
            }
            
            breakdown_df = pd.DataFrame(summary_data)
            
            # Top LLC owners
            llc_owners = llc_props.groupby('owner_name').agg({
                'id': 'count',
                'assessed_value': 'sum',
                'land_value': 'sum',
                'building_value': 'sum',
                'municipality': 'first'
            }).reset_index()
            
            llc_owners.columns = ['owner_name', 'property_count', 'total_assessed_value', 
                                 'total_land_value', 'total_building_value', 'municipality']
            llc_owners = llc_owners.sort_values('property_count', ascending=False).head(20)
            llc_owners['rank'] = range(1, len(llc_owners) + 1)
            
            top_llc_df = pd.DataFrame({
                'Rank': llc_owners['rank'],
                'LLC Owner Name': llc_owners['owner_name'],
                'Property Count': llc_owners['property_count'],
                'Total Assessed Value': llc_owners['total_assessed_value'].apply(format_currency),
                'Total Land Value': llc_owners['total_land_value'].apply(format_currency),
                'Total Building Value': llc_owners['total_building_value'].apply(format_currency)
            })
            
            # Create metadata summary
            metadata = {
                'Analysis Type': 'LLC Ownership Analysis',
                'Municipality': municipality,
                'Total Properties': total_props,
                'LLC Properties': llc_count,
                'LLC Percentage': f"{llc_pct:.2f}%",
                'Non-LLC Properties': non_llc_count,
                'Non-LLC Percentage': f"{non_llc_pct:.2f}%",
                'Date Generated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            return {
                f'{municipality} - LLC Breakdown': breakdown_df,
                f'{municipality} - Top LLC Owners': top_llc_df,
                'Summary': create_summary_sheet(metadata)
            }
        
        else:
            # Group by municipality and create sheets per town
            results = {}
            
            # Get all municipalities
            municipalities = sorted(df['municipality'].dropna().unique())
            
            print(f"\nAnalyzing {len(municipalities)} municipalities...")
            
            # Overall summary data
            overall_data = []
            
            for town in municipalities:
                town_df = df[df['municipality'] == town].copy()
                
                llc_count = town_df['is_llc'].sum()
                non_llc_count = (~town_df['is_llc']).sum()
                total_props = len(town_df)
                
                llc_pct = calculate_percentage(llc_count, total_props) if total_props > 0 else 0
                non_llc_pct = calculate_percentage(non_llc_count, total_props) if total_props > 0 else 0
                
                llc_props = town_df[town_df['is_llc']].copy()
                non_llc_props = town_df[~town_df['is_llc']].copy()
                
                # Create breakdown for this town
                breakdown_data = {
                    'Category': ['LLC/Business Entities', 'Non-LLC Owners', 'Total'],
                    'Property Count': [llc_count, non_llc_count, total_props],
                    'Percentage': [
                        f"{llc_pct:.2f}%",
                        f"{non_llc_pct:.2f}%",
                        "100.00%"
                    ],
                    'Total Assessed Value': [
                        format_currency(llc_props['assessed_value'].sum()),
                        format_currency(non_llc_props['assessed_value'].sum()),
                        format_currency(town_df['assessed_value'].sum())
                    ],
                    'Total Land Value': [
                        format_currency(llc_props['land_value'].sum()),
                        format_currency(non_llc_props['land_value'].sum()),
                        format_currency(town_df['land_value'].sum())
                    ],
                    'Total Building Value': [
                        format_currency(llc_props['building_value'].sum()),
                        format_currency(non_llc_props['building_value'].sum()),
                        format_currency(town_df['building_value'].sum())
                    ]
                }
                
                breakdown_df = pd.DataFrame(breakdown_data)
                
                # Clean sheet name (Excel limit is 31 chars)
                sheet_name = f"{town[:27]} - LLC" if len(town) > 27 else f"{town} - LLC"
                results[sheet_name] = breakdown_df
                
                # Add to overall summary
                overall_data.append({
                    'Municipality': town,
                    'Total Properties': total_props,
                    'LLC Properties': llc_count,
                    'LLC Percentage': f"{llc_pct:.2f}%",
                    'Non-LLC Properties': non_llc_count,
                    'Non-LLC Percentage': f"{non_llc_pct:.2f}%",
                    'Total Assessed Value (LLC)': format_currency(llc_props['assessed_value'].sum()),
                    'Total Assessed Value (Non-LLC)': format_currency(non_llc_props['assessed_value'].sum()),
                    'Total Assessed Value': format_currency(town_df['assessed_value'].sum())
                })
                
                print(f"  {town}: {llc_count:,} LLC ({llc_pct:.1f}%), {non_llc_count:,} non-LLC ({non_llc_pct:.1f}%)")
            
            # Create overall summary sheet
            overall_df = pd.DataFrame(overall_data)
            overall_df = overall_df.sort_values('Total Properties', ascending=False)
            results['Summary - All Towns'] = overall_df
            
            # Create metadata
            total_all = len(df)
            total_llc_all = df['is_llc'].sum()
            total_non_llc_all = (~df['is_llc']).sum()
            
            metadata = {
                'Analysis Type': 'LLC Ownership Analysis',
                'Total Municipalities': len(municipalities),
                'Total Properties': total_all,
                'Total LLC Properties': total_llc_all,
                'Total LLC Percentage': f"{calculate_percentage(total_llc_all, total_all):.2f}%",
                'Total Non-LLC Properties': total_non_llc_all,
                'Total Non-LLC Percentage': f"{calculate_percentage(total_non_llc_all, total_all):.2f}%",
                'Date Generated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            results['Metadata'] = create_summary_sheet(metadata)
            
            return results
            
    finally:
        db.close()


def main():
    """Main function to run analysis"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Analyze LLC property ownership')
    parser.add_argument('--municipality', type=str, help='Filter by specific municipality/town')
    parser.add_argument('--output-dir', type=str, help='Output directory for Excel file')
    
    args = parser.parse_args()
    
    # Run analysis
    results = analyze_llc_ownership(municipality=args.municipality)
    
    if not results:
        print("\n❌ No results to export")
        return
    
    # Determine output file
    script_dir = Path(__file__).parent.parent.parent.parent / "Analysis scripts"
    script_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if args.municipality:
        filename = f"{args.municipality}_LLC_Analysis_{timestamp}.xlsx"
    else:
        filename = f"2025_LLC_ANALYSIS_BY_TOWN_{timestamp}.xlsx"
    
    output_file = script_dir / filename
    
    # Export to Excel
    export_to_excel(results, output_file, title="LLC Ownership Analysis")
    
    print(f"\n✅ Analysis complete!")
    print(f"   Output: {output_file}")


if __name__ == "__main__":
    main()
