"""
Export Geodatabase to Excel - One file per town
Reads the Full_State_Parcels_25 layer and creates a separate Excel file for each town
All files are saved in "Excel geodatabase all towns" folder
"""
import sys
from pathlib import Path
import pandas as pd
import geopandas as gpd
from datetime import datetime
from shapely import wkt
from geopandas import GeoSeries
import warnings
warnings.filterwarnings('ignore', category=UserWarning, message='.*geographic CRS.*')

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False
    def tqdm(iterable, desc="", unit=""):
        return iterable

def export_all_towns_to_excel():
    """
    Export geodatabase to Excel - one file per town
    """
    print("=" * 80)
    print("EXPORTING GEODATABASE TO EXCEL - ONE FILE PER TOWN")
    print("=" * 80)
    
    # Geodatabase path
    script_dir = Path(__file__).parent
    gdb_path = script_dir.parent / "2025 Parcel Layer.gdb"
    
    if not gdb_path.exists():
        raise FileNotFoundError(f"Geodatabase not found: {gdb_path}")
    
    print(f"\n📂 Geodatabase: {gdb_path}")
    
    # Create output directory
    output_dir = script_dir / "Excel geodatabase all towns"
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"📁 Output directory: {output_dir}")
    
    # Read geodatabase
    print("\n📖 Reading geodatabase layer 'Full_State_Parcels_25'...")
    print("   (This may take a few minutes for the full dataset)")
    
    gdf = gpd.read_file(
        str(gdb_path),
        layer='Full_State_Parcels_25',
        driver='FileGDB'
    )
    
    print(f"   ✅ Loaded {len(gdf):,} parcels")
    print(f"   Columns: {len(gdf.columns)} total")
    
    # Check for Town_Name column
    if 'Town_Name' not in gdf.columns:
        raise ValueError("Town_Name column not found in geodatabase")
    
    # Get unique towns
    print("\n🔍 Identifying unique towns...")
    unique_towns = gdf['Town_Name'].dropna().unique()
    print(f"   Found {len(unique_towns):,} unique towns")
    
    # Sort towns alphabetically
    unique_towns = sorted([str(town).strip() for town in unique_towns if town])
    
    print(f"\n📊 Processing {len(unique_towns)} towns...")
    print("=" * 80)
    
    # Process each town
    source_crs = gdf.crs or 'EPSG:6434'
    successful_exports = 0
    failed_exports = []
    
    for i, town in enumerate(tqdm(unique_towns, desc="Exporting towns", unit="town"), 1):
        if not HAS_TQDM:
            print(f"   Processing town {i}/{len(unique_towns)}: {town}")
        try:
            # Filter by town
            town_gdf = gdf[gdf['Town_Name'].str.strip() == town]
            
            if len(town_gdf) == 0:
                print(f"\n⚠️  No parcels found for {town}")
                continue
            
            # Convert geometry to WKT for Excel (vectorized for better performance)
            print(f"   Converting geometry for {town} ({len(town_gdf):,} parcels)...")
            
            # Convert to WGS84 in one operation, handling invalid geometries
            try:
                # Make geometries valid first if possible
                town_gdf_valid = town_gdf.copy()
                town_gdf_valid['geometry'] = town_gdf_valid['geometry'].apply(
                    lambda x: x if x is None or x.is_valid else x.buffer(0) if hasattr(x, 'buffer') else x
                )
                town_gdf_wgs84 = town_gdf_valid.to_crs('EPSG:4326')
            except Exception as e:
                # If bulk conversion fails, process row by row
                print(f"      ⚠️  Bulk conversion failed, processing individually: {e}")
                town_gdf_wgs84 = town_gdf.copy()
                town_gdf_wgs84['geometry'] = town_gdf_wgs84['geometry'].apply(
                    lambda x: None if x is None or x.is_empty else (
                        GeoSeries([x], crs=source_crs).to_crs('EPSG:4326').iloc[0] 
                        if hasattr(x, 'is_valid') and x.is_valid 
                        else None
                    )
                )
            
            # Get centroids and WKT (handle invalid geometries)
            geometry_wkt_list = []
            geometry_lat_list = []
            geometry_lon_list = []
            
            for idx, geom in enumerate(town_gdf_wgs84.geometry):
                if geom is None or (hasattr(geom, 'is_empty') and geom.is_empty):
                    geometry_wkt_list.append('')
                    geometry_lat_list.append('')
                    geometry_lon_list.append('')
                else:
                    try:
                        # Get centroid
                        centroid = geom.centroid
                        geometry_lat_list.append(centroid.y)
                        geometry_lon_list.append(centroid.x)
                        
                        # Convert to 2D and get WKT
                        try:
                            geom_2d = wkt.loads(wkt.dumps(geom, output_dimension=2))
                            geometry_wkt_list.append(geom_2d.wkt)
                        except Exception:
                            # Fallback: try to get WKT directly
                            try:
                                geometry_wkt_list.append(geom.wkt)
                            except Exception:
                                geometry_wkt_list.append('')
                    except Exception as e:
                        geometry_wkt_list.append('')
                        geometry_lat_list.append('')
                        geometry_lon_list.append('')
            
            # Create DataFrame (drop geometry column, add WKT)
            df = town_gdf.drop(columns=['geometry']).copy()
            df['Geometry_WKT'] = geometry_wkt_list
            df['Latitude'] = geometry_lat_list
            df['Longitude'] = geometry_lon_list
            
            # Generate filename (sanitize town name for filename)
            safe_town_name = town.replace(' ', '_').replace('/', '_').replace('\\', '_')
            filename = f"{safe_town_name}.xlsx"
            filepath = output_dir / filename
            
            # Skip if file already exists
            if filepath.exists():
                if not HAS_TQDM:
                    print(f"   ⏭️  Skipping {town} (already exported)")
                successful_exports += 1
                continue
            
            # Export to Excel
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Parcels', index=False)
                
                # Auto-adjust column widths
                worksheet = writer.sheets['Parcels']
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
            
            successful_exports += 1
            
        except Exception as e:
            print(f"\n❌ Error exporting {town}: {e}")
            failed_exports.append((town, str(e)))
            continue
    
    # Print summary
    print("\n" + "=" * 80)
    print("EXPORT SUMMARY")
    print("=" * 80)
    print(f"✅ Successfully exported: {successful_exports:,} towns")
    print(f"❌ Failed exports: {len(failed_exports)}")
    print(f"📁 Output directory: {output_dir}")
    
    if failed_exports:
        print("\n⚠️  Failed exports:")
        for town, error in failed_exports:
            print(f"   - {town}: {error}")
    
    print("\n✅ Export complete!")
    return output_dir

if __name__ == "__main__":
    try:
        export_all_towns_to_excel()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
