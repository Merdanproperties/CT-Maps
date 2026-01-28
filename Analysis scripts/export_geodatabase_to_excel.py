"""
Export Geodatabase to Excel
Exports the Full_State_Parcels_25 layer from the geodatabase to Excel for inspection
"""
import sys
from pathlib import Path
import pandas as pd
import geopandas as gpd
from datetime import datetime
from shapely import wkt
import argparse

def export_geodatabase_to_excel(
    town: str = None,
    limit: int = None,
    sample_rows: int = 1000,
    output_dir: str = None
):
    """
    Export geodatabase to Excel
    
    Args:
        town: Filter by town name (optional, exports all if None)
        limit: Maximum number of rows to export (for testing)
        sample_rows: Number of sample rows if exporting all (default: 1000)
        output_dir: Output directory (default: Analysis scripts folder)
    """
    print("=" * 80)
    print("EXPORTING GEODATABASE TO EXCEL")
    print("=" * 80)
    
    # Geodatabase path
    script_dir = Path(__file__).parent
    gdb_path = script_dir.parent / "2025 Parcel Layer.gdb"
    
    if not gdb_path.exists():
        raise FileNotFoundError(f"Geodatabase not found: {gdb_path}")
    
    print(f"\n📂 Geodatabase: {gdb_path}")
    
    # Read geodatabase
    print("\n📖 Reading geodatabase layer 'Full_State_Parcels_25'...")
    print("   (This may take a few minutes for the full dataset)")
    
    if limit:
        print(f"   ⚠️  Limiting to first {limit:,} rows")
        gdf = gpd.read_file(
            str(gdb_path),
            layer='Full_State_Parcels_25',
            driver='FileGDB',
            rows=slice(0, limit)
        )
    else:
        gdf = gpd.read_file(
            str(gdb_path),
            layer='Full_State_Parcels_25',
            driver='FileGDB'
        )
    
    print(f"   ✅ Loaded {len(gdf):,} parcels")
    print(f"   Columns: {list(gdf.columns)[:10]}... ({len(gdf.columns)} total)")
    
    # Filter by town if specified
    if town:
        print(f"\n🔍 Filtering for town: {town}")
        original_count = len(gdf)
        gdf = gdf[gdf['Town_Name'].str.contains(town, case=False, na=False)]
        print(f"   Found {len(gdf):,} parcels (from {original_count:,} total)")
        
        if len(gdf) == 0:
            print(f"\n⚠️  No parcels found for {town}")
            return None
    elif not limit and len(gdf) > sample_rows:
        # If exporting all and it's large, offer to sample
        print(f"\n⚠️  Large dataset ({len(gdf):,} rows)")
        print(f"   Exporting sample of {sample_rows:,} rows")
        print(f"   Use --limit to export more, or --town to filter by town")
        gdf = gdf.head(sample_rows)
    
    # Convert geometry to WKT for Excel
    print("\n🔄 Converting geometry to WKT format...")
    source_crs = gdf.crs or 'EPSG:6434'
    
    geometry_wkt_list = []
    geometry_lat_list = []
    geometry_lon_list = []
    
    for idx, row in gdf.iterrows():
        geom = row.geometry
        if geom is None:
            geometry_wkt_list.append('')
            geometry_lat_list.append('')
            geometry_lon_list.append('')
            continue
        
        try:
            from geopandas import GeoSeries
            geom_series = GeoSeries([geom], crs=source_crs)
            geom_wgs84 = geom_series.to_crs('EPSG:4326').iloc[0]
            geom_2d = wkt.loads(wkt.dumps(geom_wgs84, output_dimension=2))
            geometry_wkt = geom_2d.wkt
            
            # Get centroid for lat/lon
            centroid = geom_wgs84.centroid
            geometry_lat_list.append(centroid.y)
            geometry_lon_list.append(centroid.x)
            geometry_wkt_list.append(geometry_wkt)
        except Exception as e:
            geometry_wkt_list.append('')
            geometry_lat_list.append('')
            geometry_lon_list.append('')
    
    # Create DataFrame (drop geometry column, add WKT)
    df = gdf.drop(columns=['geometry']).copy()
    df['Geometry_WKT'] = geometry_wkt_list
    df['Latitude'] = geometry_lat_list
    df['Longitude'] = geometry_lon_list
    
    # Create output directory
    if output_dir is None:
        output_path = script_dir
    else:
        output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Generate filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    town_str = f"_{town.replace(' ', '_')}" if town else ""
    limit_str = f"_limit{limit}" if limit else ""
    filename = f"geodatabase_export{town_str}{limit_str}_{timestamp}.xlsx"
    filepath = output_path / filename
    
    # Export to Excel
    print(f"\n📝 Exporting to Excel...")
    print(f"   File: {filepath}")
    
    with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Geodatabase', index=False)
        
        # Auto-adjust column widths
        worksheet = writer.sheets['Geodatabase']
        for idx, col in enumerate(df.columns, 1):
            max_length = max(
                df[col].astype(str).map(len).max() if len(df) > 0 else 0,
                len(str(col))
            )
            # Excel column letter calculation
            if idx <= 26:
                col_letter = chr(64 + idx)
            else:
                col_letter = chr(64 + (idx - 1) // 26) + chr(64 + ((idx - 1) % 26) + 1)
            worksheet.column_dimensions[col_letter].width = min(max_length + 2, 50)
    
    print(f"\n✅ Exported {len(df):,} rows to:")
    print(f"   {filepath}")
    print(f"\n📊 Columns in export:")
    for col in df.columns:
        print(f"   - {col}")
    
    return str(filepath)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Export geodatabase to Excel for inspection',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Export sample (first 1000 rows)
  python export_geodatabase_to_excel.py --limit 1000
  
  # Export specific town
  python export_geodatabase_to_excel.py --town Bridgeport
  
  # Export all (samples first 1000 if large)
  python export_geodatabase_to_excel.py
        """
    )
    
    parser.add_argument('--town', type=str, help='Filter by town name')
    parser.add_argument('--limit', type=int, help='Maximum number of rows to export')
    parser.add_argument('--sample-rows', type=int, default=1000, help='Number of sample rows if exporting all (default: 1000)')
    parser.add_argument('--output-dir', type=str, help='Output directory (default: Analysis scripts folder)')
    
    args = parser.parse_args()
    
    try:
        export_geodatabase_to_excel(
            town=args.town,
            limit=args.limit,
            sample_rows=args.sample_rows,
            output_dir=args.output_dir
        )
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
