"""
Top Owners Analysis by Owner Name

Groups properties by owner name only (regardless of mailing address)
to identify owners with multiple properties across different addresses.

Output: Excel file with top owners grouped by name, per town
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
    calculate_percentage
)


def analyze_top_owners_by_name(
    municipality: Optional[str] = None,
    top_n: int = 20,
    min_properties: int = 1
) -> Dict[str, pd.DataFrame]:
    """
    Analyze top property owners grouped by owner name only
    
    Args:
        municipality: Optional town/municipality to filter by
        top_n: Number of top owners to return per town
        min_properties: Minimum number of properties to include
        
    Returns:
        Dictionary of {sheet_name: DataFrame} for Excel export
    """
    print("=" * 80)
    print("TOP OWNERS BY NAME ANALYSIS")
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
        
        # Group by owner name only
        grouped = df.groupby('owner_name').agg({
            'id': 'count',
            'municipality': lambda x: ', '.join(sorted(x.unique())),
            'owner_address': lambda x: ', '.join(x.dropna().unique()[:3]),  # Sample addresses
            'owner_city': lambda x: ', '.join(x.dropna().unique()[:3]),  # Sample cities
            'owner_state': lambda x: ', '.join(x.dropna().unique()),
            'assessed_value': 'sum',
            'land_value': 'sum',
            'building_value': 'sum',
            'total_value': 'sum',
            'parcel_id': lambda x: ', '.join(x.astype(str).head(5).tolist())  # Sample parcel IDs
        }).reset_index()
        
        grouped.columns = [
            'owner_name',
            'property_count',
            'municipalities',
            'sample_addresses',
            'sample_cities',
            'owner_states',
            'total_assessed_value',
            'total_land_value',
            'total_building_value',
            'total_value',
            'sample_parcel_ids'
        ]
        
        # Filter by minimum properties
        grouped = grouped[grouped['property_count'] >= min_properties].copy()
        
        # Calculate total for percentage calculation
        total_properties = grouped['property_count'].sum()
        grouped['percentage'] = grouped['property_count'].apply(
            lambda x: calculate_percentage(x, total_properties)
        )
        
        # Sort by property count descending
        grouped = grouped.sort_values('property_count', ascending=False)
        
        # If municipality specified, create single sheet
        if municipality:
            # Take top N
            top_owners = grouped.head(top_n).copy()
            
            # Create formatted output
            output_df = pd.DataFrame({
                'Rank': range(1, len(top_owners) + 1),
                'Owner Name': top_owners['owner_name'],
                'Property Count': top_owners['property_count'],
                'Percentage': top_owners['percentage'].apply(lambda x: f"{x:.2f}%"),
                'Total Assessed Value': top_owners['total_assessed_value'].apply(format_currency),
                'Total Land Value': top_owners['total_land_value'].apply(format_currency),
                'Total Building Value': top_owners['total_building_value'].apply(format_currency),
                'Sample Addresses': top_owners['sample_addresses'],
                'Sample Cities': top_owners['sample_cities'],
                'Owner States': top_owners['owner_states'],
                'Sample Parcel IDs': top_owners['sample_parcel_ids']
            })
            
            # Create summary
            summary = {
                'Analysis Type': 'Top Owners by Name',
                'Municipality': municipality,
                'Total Properties Analyzed': len(df),
                'Unique Owner Names': len(grouped),
                'Top N Owners': top_n,
                'Date Generated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            return {
                f'{municipality} - Top Owners': output_df,
                'Summary': create_summary_sheet(summary)
            }
        
        else:
            # Group by municipality and create sheets per town
            results = {}
            
            # Get all municipalities
            municipalities = sorted(df['municipality'].dropna().unique())
            
            print(f"\nAnalyzing {len(municipalities)} municipalities...")
            
            for town in municipalities:
                town_df = df[df['municipality'] == town].copy()
                
                # Re-group for this town
                town_grouped = town_df.groupby('owner_name').agg({
                    'id': 'count',
                    'owner_address': lambda x: ', '.join(x.dropna().unique()[:3]),
                    'owner_city': lambda x: ', '.join(x.dropna().unique()[:3]),
                    'owner_state': lambda x: ', '.join(x.dropna().unique()),
                    'assessed_value': 'sum',
                    'land_value': 'sum',
                    'building_value': 'sum',
                    'total_value': 'sum',
                    'parcel_id': lambda x: ', '.join(x.astype(str).head(5).tolist())
                }).reset_index()
                
                town_grouped.columns = [
                    'owner_name',
                    'property_count',
                    'sample_addresses',
                    'sample_cities',
                    'owner_states',
                    'total_assessed_value',
                    'total_land_value',
                    'total_building_value',
                    'total_value',
                    'sample_parcel_ids'
                ]
                
                town_grouped = town_grouped[town_grouped['property_count'] >= min_properties].copy()
                
                # Calculate percentage for this town
                town_total = town_grouped['property_count'].sum()
                town_grouped['percentage'] = town_grouped['property_count'].apply(
                    lambda x: calculate_percentage(x, town_total) if town_total > 0 else 0
                )
                
                town_grouped = town_grouped.sort_values('property_count', ascending=False)
                top_owners = town_grouped.head(top_n).copy()
                
                if len(top_owners) > 0:
                    output_df = pd.DataFrame({
                        'Rank': range(1, len(top_owners) + 1),
                        'Owner Name': top_owners['owner_name'],
                        'Property Count': top_owners['property_count'],
                        'Percentage': top_owners['percentage'].apply(lambda x: f"{x:.2f}%"),
                        'Total Assessed Value': top_owners['total_assessed_value'].apply(format_currency),
                        'Total Land Value': top_owners['total_land_value'].apply(format_currency),
                        'Total Building Value': top_owners['total_building_value'].apply(format_currency),
                        'Sample Addresses': top_owners['sample_addresses'],
                        'Sample Cities': top_owners['sample_cities'],
                        'Owner States': top_owners['owner_states'],
                        'Sample Parcel IDs': top_owners['sample_parcel_ids']
                    })
                    
                    # Clean sheet name (Excel limit is 31 chars)
                    sheet_name = f"{town[:25]} - Top Owners" if len(town) > 25 else f"{town} - Top Owners"
                    results[sheet_name] = output_df
                    
                    print(f"  {town}: {len(top_owners)} top owners")
            
            # Create overall summary
            summary = {
                'Analysis Type': 'Top Owners by Name',
                'Total Municipalities': len(municipalities),
                'Total Properties Analyzed': len(df),
                'Top N Owners per Town': top_n,
                'Minimum Properties': min_properties,
                'Date Generated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            results['Summary'] = create_summary_sheet(summary)
            
            return results
            
    finally:
        db.close()


def main():
    """Main function to run analysis"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Analyze top property owners by name')
    parser.add_argument('--municipality', type=str, help='Filter by specific municipality/town')
    parser.add_argument('--top-n', type=int, default=20, help='Number of top owners to return (default: 20)')
    parser.add_argument('--min-properties', type=int, default=1, help='Minimum properties to include (default: 1)')
    parser.add_argument('--output-dir', type=str, help='Output directory for Excel file')
    
    args = parser.parse_args()
    
    # Run analysis
    results = analyze_top_owners_by_name(
        municipality=args.municipality,
        top_n=args.top_n,
        min_properties=args.min_properties
    )
    
    if not results:
        print("\n❌ No results to export")
        return
    
    # Determine output file
    script_dir = Path(__file__).parent.parent.parent.parent / "Analysis scripts"
    script_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if args.municipality:
        filename = f"{args.municipality}_Top_Owners_By_Name_{timestamp}.xlsx"
    else:
        filename = f"2025_TOP_OWNERS_BY_NAME_PER_TOWN_{timestamp}.xlsx"
    
    output_file = script_dir / filename
    
    # Export to Excel
    export_to_excel(results, output_file, title="Top Owners by Name Analysis")
    
    print(f"\n✅ Analysis complete!")
    print(f"   Output: {output_file}")


if __name__ == "__main__":
    main()
