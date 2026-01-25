"""
Script to inspect the geodatabase structure and show what fields are available
"""
import sys
from pathlib import Path

try:
    import fiona
    import geopandas as gpd
    import pandas as pd
except ImportError:
    print("❌ Missing required libraries. Installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "geopandas", "fiona"])
    import fiona
    import geopandas as gpd
    import pandas as pd

def inspect_geodatabase(gdb_path: str):
    """Inspect the geodatabase and show its structure"""
    print(f"\n{'='*60}")
    print(f"Inspecting: {gdb_path}")
    print(f"{'='*60}\n")
    
    if not Path(gdb_path).exists():
        print(f"❌ Error: Geodatabase not found at {gdb_path}")
        return
    
    try:
        # List all layers
        print("📋 Available Layers:")
        print("-" * 60)
        layers = fiona.listlayers(gdb_path)
        for i, layer in enumerate(layers, 1):
            print(f"  {i}. {layer}")
        
        if not layers:
            print("  ❌ No layers found!")
            return
        
        # Inspect the first layer (usually the main parcel layer)
        main_layer = layers[0]
        print(f"\n📊 Inspecting Layer: '{main_layer}'")
        print("-" * 60)
        
        # Read the layer
        gdf = gpd.read_file(gdb_path, layer=main_layer)
        
        print(f"\n✅ Successfully loaded layer")
        print(f"   Total parcels: {len(gdf):,}")
        print(f"   Coordinate system: {gdf.crs}")
        
        if len(gdf) > 0:
            bounds = gdf.total_bounds
            print(f"   Bounds: [{bounds[0]:.6f}, {bounds[1]:.6f}, {bounds[2]:.6f}, {bounds[3]:.6f}]")
        
        # Show columns
        print(f"\n📝 Columns ({len(gdf.columns)} total):")
        print("-" * 60)
        
        # Group columns by type
        geometry_cols = [c for c in gdf.columns if gdf[c].dtype == 'geometry']
        other_cols = [c for c in gdf.columns if c not in geometry_cols]
        
        if geometry_cols:
            print(f"\n   🗺️  Geometry columns:")
            for col in geometry_cols:
                print(f"      • {col}")
        
        print(f"\n   📋 Data columns ({len(other_cols)}):")
        for col in sorted(other_cols):
            dtype = str(gdf[col].dtype)
            non_null = gdf[col].notna().sum()
            null_count = len(gdf) - non_null
            null_pct = (null_count / len(gdf) * 100) if len(gdf) > 0 else 0
            
            # Get sample value
            sample_val = "N/A"
            if non_null > 0:
                sample = gdf[col].dropna().iloc[0]
                sample_str = str(sample)
                sample_val = sample_str[:40] + "..." if len(sample_str) > 40 else sample_str
            
            print(f"      • {col:30s} | {dtype:10s} | {non_null:6,} non-null ({null_pct:5.1f}% null)")
            if non_null > 0:
                print(f"        Sample: {sample_val}")
        
        # Show sample rows
        print(f"\n📄 Sample Data (first 3 rows):")
        print("-" * 60)
        
        # Create a display dataframe without geometry
        display_df = gdf.drop(columns=geometry_cols) if geometry_cols else gdf
        
        # Show first few rows, but limit column width
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)
        pd.set_option('display.max_colwidth', 30)
        
        print(display_df.head(3).to_string())
        
        # Field name suggestions
        print(f"\n💡 Field Mapping Suggestions:")
        print("-" * 60)
        
        col_lower = {col.lower(): col for col in other_cols}
        
        suggestions = {
            'parcel_id': ['parcel', 'parcelid', 'parcel_id', 'objectid', 'fid'],
            'address': ['address', 'site_addr', 'site_address', 'prop_addr'],
            'municipality': ['municipality', 'town', 'city', 'municipal'],
            'owner_name': ['owner', 'owner_name', 'owner_nm', 'prop_owner'],
            'owner_address': ['owner_addr', 'owner_address', 'mail_addr', 'mailing'],
            'assessed_value': ['assessed', 'assessed_val', 'total_assessed', 'assess_val'],
            'land_value': ['land', 'land_value', 'land_val', 'land_assessed'],
            'building_value': ['building', 'bldg', 'building_value', 'bldg_val', 'improvement'],
            'property_type': ['prop_type', 'property_type', 'use_code', 'class'],
            'land_use': ['land_use', 'use', 'use_code', 'zoning'],
            'lot_size': ['lot', 'lot_size', 'lot_sqft', 'acreage', 'acres'],
            'building_area': ['bldg_area', 'building_area', 'sqft', 'living_area'],
            'year_built': ['year', 'year_built', 'built', 'yr_built'],
        }
        
        for our_field, possible_names in suggestions.items():
            found = None
            for name in possible_names:
                if name in col_lower:
                    found = col_lower[name]
                    break
            if found:
                print(f"   ✅ {our_field:20s} → {found}")
            else:
                print(f"   ❌ {our_field:20s} → NOT FOUND")
        
        # Save summary to file
        summary_file = Path(gdb_path).parent / "geodatabase_inspection.txt"
        with open(summary_file, 'w') as f:
            f.write(f"Geodatabase Inspection Report\n")
            f.write(f"{'='*60}\n\n")
            f.write(f"File: {gdb_path}\n")
            f.write(f"Layer: {main_layer}\n")
            f.write(f"Total Parcels: {len(gdf):,}\n")
            f.write(f"Coordinate System: {gdf.crs}\n\n")
            f.write(f"Columns:\n")
            for col in sorted(other_cols):
                f.write(f"  - {col}\n")
        
        print(f"\n💾 Summary saved to: {summary_file}")
        print(f"\n✅ Inspection complete!")
        
    except Exception as e:
        print(f"\n❌ Error inspecting geodatabase: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Path to geodatabase
    gdb_path = Path(__file__).parent.parent.parent / "2025 Parcel Layer.gdb"
    
    if not gdb_path.exists():
        print(f"❌ Error: Geodatabase not found at {gdb_path}")
        print(f"   Current directory: {Path.cwd()}")
        sys.exit(1)
    
    inspect_geodatabase(str(gdb_path))
