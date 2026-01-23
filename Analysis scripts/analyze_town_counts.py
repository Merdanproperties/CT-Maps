"""
Analysis script to compare property counts across all 169 CT towns
Compares: Geodatabase vs CAMA Excel vs CAMA CSV
Outputs: Excel file with detailed comparison
"""
import sys
from pathlib import Path
import pandas as pd
import geopandas as gpd
from typing import Dict
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent / "backend"))

def analyze_geodatabase(gdb_path: str) -> Dict[str, int]:
    """
    Count properties by town in the geodatabase
    Returns: {town_name: count}
    """
    print("=" * 80)
    print("ANALYZING GEODATABASE")
    print("=" * 80)
    
    import fiona
    layers = fiona.listlayers(gdb_path)
    if not layers:
        raise Exception("No layers found in geodatabase")
    
    layer_name = layers[0]
    print(f"Reading layer: {layer_name}")
    
    # Read geodatabase
    print("Loading geodatabase (this may take a few minutes)...")
    gdf = gpd.read_file(gdb_path, layer=layer_name, driver='FileGDB')
    print(f"Total parcels in geodatabase: {len(gdf):,}")
    
    # Count by Town_Name
    if 'Town_Name' not in gdf.columns:
        raise Exception("Town_Name column not found in geodatabase")
    
    town_counts = gdf['Town_Name'].value_counts().to_dict()
    
    # Handle null/empty values
    null_count = gdf['Town_Name'].isna().sum()
    if null_count > 0:
        town_counts['[NULL/EMPTY]'] = null_count
    
    print(f"Found {len(town_counts)} unique towns")
    print(f"Bridgeport count: {town_counts.get('Bridgeport', 0):,}")
    
    return town_counts

def analyze_cama_excel_files(data_dir: str) -> Dict[str, int]:
    """
    Count properties by town in CAMA Excel files
    Looks for files matching pattern: {Town}_CAMA_2025_CLEANED.xlsx
    Returns: {town_name: count}
    """
    print("\n" + "=" * 80)
    print("ANALYZING CAMA EXCEL FILES")
    print("=" * 80)
    
    data_path = Path(data_dir)
    excel_dir = data_path / "2025 Post Duplicate Clean"
    
    if not excel_dir.exists():
        print(f"⚠️  Excel directory not found: {excel_dir}")
        return {}
    
    town_counts = {}
    excel_files = list(excel_dir.glob("*_CAMA_2025_CLEANED.xlsx"))
    
    print(f"Found {len(excel_files)} CAMA Excel files")
    
    for excel_file in excel_files:
        try:
            # Extract town name from filename
            # Format: {Town}_CAMA_2025_CLEANED.xlsx
            town_name = excel_file.stem.replace("_CAMA_2025_CLEANED", "")
            
            # Read Excel file
            df = pd.read_excel(excel_file, engine='openpyxl')
            
            # Skip tracking row if present
            if len(df) > 1:
                first_row_values = df.iloc[0].astype(str).str.lower()
                if 'replaced' in ' '.join(first_row_values) or 'owner' in str(df.iloc[0].get('Full Name', '')).lower():
                    df = df.iloc[1:].reset_index(drop=True)
            
            count = len(df)
            town_counts[town_name] = count
            print(f"  {town_name:30s}: {count:6,} properties")
            
        except Exception as e:
            print(f"  ⚠️  Error reading {excel_file.name}: {e}")
    
    return town_counts

def analyze_cama_csv_files(data_dir: str) -> Dict[str, int]:
    """
    Count properties by town in CAMA CSV files
    Looks for files matching pattern: {Town}_CAMA_2025.csv
    Returns: {town_name: count}
    """
    print("\n" + "=" * 80)
    print("ANALYZING CAMA CSV FILES")
    print("=" * 80)
    
    data_path = Path(data_dir)
    csv_dir = data_path / "2025 Parcel Collection"
    
    if not csv_dir.exists():
        print(f"⚠️  CSV directory not found: {csv_dir}")
        return {}
    
    town_counts = {}
    csv_files = list(csv_dir.glob("*_CAMA_2025.csv"))
    
    print(f"Found {len(csv_files)} CAMA CSV files")
    
    for csv_file in csv_files:
        try:
            # Extract town name from filename
            # Format: {Town}_CAMA_2025.csv
            town_name = csv_file.stem.replace("_CAMA_2025", "")
            
            # Read CSV file
            df = pd.read_csv(csv_file, low_memory=False)
            count = len(df)
            town_counts[town_name] = count
            print(f"  {town_name:30s}: {count:6,} properties")
            
        except Exception as e:
            print(f"  ⚠️  Error reading {csv_file.name}: {e}")
    
    return town_counts

def generate_comparison_report(
    gdb_counts: Dict[str, int],
    excel_counts: Dict[str, int],
    csv_counts: Dict[str, int],
    output_file: str
) -> pd.DataFrame:
    """
    Generate a comprehensive comparison report and save to Excel
    """
    print("\n" + "=" * 80)
    print("GENERATING COMPARISON REPORT")
    print("=" * 80)
    
    # Get all unique towns
    all_towns = set(gdb_counts.keys())
    all_towns.update(excel_counts.keys())
    all_towns.update(csv_counts.keys())
    all_towns.discard('[NULL/EMPTY]')  # Remove null placeholder
    all_towns = sorted(all_towns)
    
    print(f"Total unique towns found: {len(all_towns)}")
    
    # Build comparison data
    report_data = []
    for town in all_towns:
        gdb_count = gdb_counts.get(town, 0)
        excel_count = excel_counts.get(town, 0)
        csv_count = csv_counts.get(town, 0)
        
        # Calculate differences
        excel_diff = excel_count - gdb_count
        csv_diff = csv_count - gdb_count
        excel_csv_diff = excel_count - csv_count
        
        # Calculate percentages
        excel_pct = (excel_count / gdb_count * 100) if gdb_count > 0 else None
        csv_pct = (csv_count / gdb_count * 100) if gdb_count > 0 else None
        excel_csv_pct = (excel_count / csv_count * 100) if csv_count > 0 else None
        
        report_data.append({
            'Town': town,
            'Geodatabase_Count': gdb_count,
            'CAMA_Excel_Count': excel_count,
            'CAMA_CSV_Count': csv_count,
            'Excel_vs_GDB_Diff': excel_diff,
            'CSV_vs_GDB_Diff': csv_diff,
            'Excel_vs_CSV_Diff': excel_csv_diff,
            'Excel_Pct_of_GDB': round(excel_pct, 1) if gdb_count > 0 and excel_pct is not None else None,
            'CSV_Pct_of_GDB': round(csv_pct, 1) if gdb_count > 0 and csv_pct is not None else None,
            'Excel_Pct_of_CSV': round(excel_csv_pct, 1) if csv_count > 0 and excel_csv_pct is not None else None,
        })
    
    # Create DataFrame
    df = pd.DataFrame(report_data)
    
    # Sort by Geodatabase count (descending)
    df = df.sort_values('Geodatabase_Count', ascending=False)
    
    # Save to Excel with formatting
    print(f"\nSaving report to Excel: {output_file}")
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        # Main comparison sheet
        df.to_excel(writer, sheet_name='Town Comparison', index=False)
        
        # Get workbook and worksheet for formatting
        workbook = writer.book
        worksheet = writer.sheets['Town Comparison']
        
        # Auto-adjust column widths
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            worksheet.column_dimensions[column_letter].width = adjusted_width
        
        # Summary sheet
        summary_data = {
            'Metric': [
                'Total Towns Analyzed',
                'Total Properties (Geodatabase)',
                'Total Properties (CAMA Excel)',
                'Total Properties (CAMA CSV)',
                'Towns with Excel Files',
                'Towns with CSV Files',
                'Towns Missing Excel Files',
                'Towns Missing CSV Files',
            ],
            'Value': [
                len(df),
                int(df['Geodatabase_Count'].sum()),
                int(df['CAMA_Excel_Count'].sum()),
                int(df['CAMA_CSV_Count'].sum()),
                int((df['CAMA_Excel_Count'] > 0).sum()),
                int((df['CAMA_CSV_Count'] > 0).sum()),
                int((df['CAMA_Excel_Count'] == 0).sum()),
                int((df['CAMA_CSV_Count'] == 0).sum()),
            ]
        }
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name='Summary', index=False)
    
    print(f"✅ Excel report saved to: {output_file}")
    
    # Print summary statistics
    print("\n" + "=" * 80)
    print("SUMMARY STATISTICS")
    print("=" * 80)
    
    total_gdb = df['Geodatabase_Count'].sum()
    total_excel = df['CAMA_Excel_Count'].sum()
    total_csv = df['CAMA_CSV_Count'].sum()
    
    towns_with_excel = (df['CAMA_Excel_Count'] > 0).sum()
    towns_with_csv = (df['CAMA_CSV_Count'] > 0).sum()
    
    print(f"Total towns analyzed: {len(df)}")
    print(f"\nTotal Properties:")
    print(f"  Geodatabase: {total_gdb:,}")
    print(f"  CAMA Excel:  {total_excel:,}")
    print(f"  CAMA CSV:    {total_csv:,}")
    print(f"\nTowns with CAMA data:")
    print(f"  Towns with Excel files: {towns_with_excel}")
    print(f"  Towns with CSV files:   {towns_with_csv}")
    
    return df

def main():
    # Paths
    script_dir = Path(__file__).parent
    gdb_path = script_dir.parent / "2025 Parcel Layer.gdb"
    data_dir = Path("/Users/jacobmermelstein/Desktop/CT Data")
    
    # Output file in the same directory as script
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = script_dir / f"town_property_count_analysis_{timestamp}.xlsx"
    
    print("=" * 80)
    print("CT TOWNS PROPERTY COUNT ANALYSIS")
    print("=" * 80)
    print(f"Geodatabase: {gdb_path}")
    print(f"Data Directory: {data_dir}")
    print(f"Output File: {output_file}")
    print("=" * 80)
    
    try:
        # Analyze each source
        gdb_counts = analyze_geodatabase(str(gdb_path))
        excel_counts = analyze_cama_excel_files(str(data_dir))
        csv_counts = analyze_cama_csv_files(str(data_dir))
        
        # Generate comparison report
        df = generate_comparison_report(gdb_counts, excel_counts, csv_counts, str(output_file))
        
        print("\n" + "=" * 80)
        print("✅ ANALYSIS COMPLETE")
        print("=" * 80)
        print(f"Excel report saved to: {output_file}")
        
    except Exception as e:
        print(f"\n❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    main()
