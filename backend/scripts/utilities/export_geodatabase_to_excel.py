"""
Export Geodatabase to Excel
Exports a sample of the geodatabase to Excel so you can see all columns
"""
import sys
from pathlib import Path
import pandas as pd
from datetime import datetime

try:
    import fiona
    import geopandas as gpd
except ImportError:
    print("❌ Missing required libraries. Please install: pip install geopandas fiona")
    sys.exit(1)

def export_geodatabase_to_excel(gdb_path: str, limit: int = 100, output_dir: str = None):
    """
    Export geodatabase to Excel with all columns
    
    Args:
        gdb_path: Path to the geodatabase file
        limit: Number of records to export (default: 100)
        output_dir: Output directory (default: Analysis scripts folder)
    """
    print("=" * 80)
    print("EXPORTING GEODATABASE TO EXCEL")
    print("=" * 80)
    
    if not Path(gdb_path).exists():
        print(f"❌ Error: Geodatabase not found at {gdb_path}")
        return
    
    try:
        # List all layers
        print(f"\n📋 Reading geodatabase: {gdb_path}")
        layers = fiona.listlayers(gdb_path)
        
        if not layers:
            print("  ❌ No layers found!")
            return
        
        print(f"   Found {len(layers)} layer(s): {', '.join(layers)}")
        
        # Use the first layer (usually the main parcel layer)
        main_layer = layers[0]
        print(f"\n📊 Reading layer: '{main_layer}'")
        
        # Read a sample of the layer
        print(f"   Reading first {limit:,} records...")
        gdf = gpd.read_file(gdb_path, layer=main_layer, rows=limit)
        
        print(f"   ✅ Loaded {len(gdf):,} records")
        print(f"   📝 Found {len(gdf.columns)} columns")
        
        # Show column names
        print(f"\n📋 Columns in geodatabase:")
        print("-" * 80)
        for i, col in enumerate(gdf.columns, 1):
            dtype = str(gdf[col].dtype)
            non_null = gdf[col].notna().sum()
            print(f"   {i:2d}. {col:30s} ({dtype:15s}) - {non_null:4d} non-null values")
        
        # Convert geometry to WKT and add lat/lon
        print(f"\n🗺️  Processing geometry...")
        if 'geometry' in gdf.columns:
            # Add centroid coordinates
            gdf['centroid_lat'] = gdf.geometry.centroid.y
            gdf['centroid_lon'] = gdf.geometry.centroid.x
            # Add WKT
            gdf['geometry_wkt'] = gdf.geometry.apply(lambda x: x.wkt if x is not None else '')
        
        # Create output directory
        if output_dir is None:
            workspace_root = Path(__file__).parent.parent.parent.parent
            output_path = workspace_root / "Analysis scripts"
        else:
            output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"geodatabase_columns_sample_{timestamp}.xlsx"
        filepath = output_path / filename
        
        # Export to Excel
        print(f"\n📝 Exporting to Excel...")
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            # Export data columns (excluding geometry object)
            data_cols = [c for c in gdf.columns if c != 'geometry']
            df_export = gdf[data_cols].copy()
            
            df_export.to_excel(writer, sheet_name='Geodatabase Sample', index=False)
            
            # Auto-adjust column widths
            worksheet = writer.sheets['Geodatabase Sample']
            for idx, col in enumerate(df_export.columns, 1):
                max_length = max(
                    df_export[col].astype(str).map(len).max() if len(df_export) > 0 else 0,
                    len(str(col))
                )
                # Excel column letter calculation
                if idx <= 26:
                    col_letter = chr(64 + idx)
                else:
                    col_letter = chr(64 + (idx - 1) // 26) + chr(64 + ((idx - 1) % 26) + 1)
                worksheet.column_dimensions[col_letter].width = min(max_length + 2, 50)
        
        print(f"\n✅ Exported {len(gdf):,} records with {len(data_cols)} columns to:")
        print(f"   {filepath}")
        
        return str(filepath)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Export geodatabase to Excel')
    parser.add_argument('--gdb-path', type=str, help='Path to geodatabase file')
    parser.add_argument('--limit', type=int, default=100, help='Number of records to export')
    parser.add_argument('--output-dir', type=str, help='Output directory')
    
    args = parser.parse_args()
    
    # Default geodatabase path
    if not args.gdb_path:
        gdb_path = Path(__file__).parent.parent.parent.parent / "2025 Parcel Layer.gdb"
        if not gdb_path.exists():
            print(f"❌ Error: Geodatabase not found at default path: {gdb_path}")
            print(f"   Please specify --gdb-path")
            sys.exit(1)
    else:
        gdb_path = args.gdb_path
    
    export_geodatabase_to_excel(
        gdb_path=str(gdb_path),
        limit=args.limit,
        output_dir=args.output_dir
    )
