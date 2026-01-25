"""
Script to analyze which towns have addresses in the geodatabase Location field
"""
import sys
from pathlib import Path
import geopandas as gpd
import pandas as pd

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

GDB_PATH = "/Users/jacobmermelstein/Desktop/CT Maps/2025 Parcel Layer.gdb"

def analyze_town_addresses():
    """
    Analyze all towns to see which have addresses in Location field
    """
    print("=" * 80)
    print("Analyzing Town Address Coverage in Geodatabase")
    print("=" * 80)
    
    # Read geodatabase
    print("\nReading geodatabase...")
    gdf = gpd.read_file(GDB_PATH, layer='Full_State_Parcels_25', driver='FileGDB')
    print(f"  Total parcels: {len(gdf):,}")
    
    # Check if Location column exists
    if 'Location' not in gdf.columns:
        print("  ❌ Location column not found in geodatabase!")
        print(f"  Available columns: {list(gdf.columns)[:20]}")
        return
    
    # Group by Town_Name and analyze Location field
    print("\nAnalyzing by town...")
    
    # Get unique towns
    towns = gdf['Town_Name'].dropna().unique()
    print(f"  Found {len(towns)} unique towns")
    
    # Analyze each town
    results = []
    for town in sorted(towns):
        town_data = gdf[gdf['Town_Name'] == town]
        total = len(town_data)
        
        # Count non-null, non-empty Location values
        location_data = town_data['Location']
        has_address = location_data.notna() & (location_data != '') & (location_data != 'None')
        address_count = has_address.sum()
        address_percent = (address_count / total * 100) if total > 0 else 0
        
        # Categorize
        if address_percent >= 90:
            category = "✅ Has Addresses (90%+)"
        elif address_percent >= 50:
            category = "⚠️  Partial Addresses (50-90%)"
        elif address_percent > 0:
            category = "⚠️  Few Addresses (<50%)"
        else:
            category = "❌ No Addresses (0%)"
        
        results.append({
            'town': town,
            'total_parcels': total,
            'addresses': address_count,
            'percent': address_percent,
            'category': category
        })
    
    # Sort by address percentage (descending)
    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values('percent', ascending=False)
    
    # Print summary
    print("\n" + "=" * 80)
    print("SUMMARY BY CATEGORY")
    print("=" * 80)
    
    has_addresses = results_df[results_df['percent'] >= 90]
    partial = results_df[(results_df['percent'] >= 50) & (results_df['percent'] < 90)]
    few = results_df[(results_df['percent'] > 0) & (results_df['percent'] < 50)]
    none = results_df[results_df['percent'] == 0]
    
    print(f"\n✅ Has Addresses (90%+): {len(has_addresses)} towns")
    print(f"⚠️  Partial Addresses (50-90%): {len(partial)} towns")
    print(f"⚠️  Few Addresses (<50%): {len(few)} towns")
    print(f"❌ No Addresses (0%): {len(none)} towns")
    print(f"\nTotal: {len(results_df)} towns")
    
    # Print detailed results
    print("\n" + "=" * 80)
    print("DETAILED RESULTS (sorted by address coverage)")
    print("=" * 80)
    print(f"\n{'Town':<30} {'Total':<12} {'Addresses':<12} {'Coverage':<10} {'Category'}")
    print("-" * 80)
    
    for _, row in results_df.iterrows():
        print(f"{row['town']:<30} {row['total_parcels']:>11,} {row['addresses']:>11,} {row['percent']:>9.1f}%  {row['category']}")
    
    # Save to CSV
    output_file = "town_address_analysis.csv"
    results_df.to_csv(output_file, index=False)
    print(f"\n✅ Results saved to: {output_file}")
    
    # Print towns like Bridgeport (has addresses)
    print("\n" + "=" * 80)
    print("TOWNS WITH ADDRESSES (like Bridgeport) - Can use address matching")
    print("=" * 80)
    bridgeport_like = has_addresses['town'].tolist()
    print(f"\n{len(bridgeport_like)} towns:")
    for i, town in enumerate(bridgeport_like, 1):
        print(f"  {i:3}. {town}")
    
    # Print towns like Torrington (no addresses)
    print("\n" + "=" * 80)
    print("TOWNS WITHOUT ADDRESSES (like Torrington) - Need spatial matching")
    print("=" * 80)
    torrington_like = none['town'].tolist()
    print(f"\n{len(torrington_like)} towns:")
    for i, town in enumerate(torrington_like, 1):
        print(f"  {i:3}. {town}")
    
    # Also show partial and few categories
    if len(partial) > 0:
        print("\n" + "=" * 80)
        print("TOWNS WITH PARTIAL ADDRESSES (50-90%)")
        print("=" * 80)
        partial_list = partial['town'].tolist()
        print(f"\n{len(partial_list)} towns:")
        for i, town in enumerate(partial_list, 1):
            print(f"  {i:3}. {town}")
    
    if len(few) > 0:
        print("\n" + "=" * 80)
        print("TOWNS WITH FEW ADDRESSES (<50%)")
        print("=" * 80)
        few_list = few['town'].tolist()
        print(f"\n{len(few_list)} towns:")
        for i, town in enumerate(few_list, 1):
            print(f"  {i:3}. {town}")

if __name__ == "__main__":
    analyze_town_addresses()
