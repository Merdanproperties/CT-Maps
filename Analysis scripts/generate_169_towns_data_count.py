"""
Generate Excel report with data counts for all 169 Connecticut towns
Counts properties from: Geodatabase, CSV files, and Post-Duplicate Excel files
Outputs: Excel file with all 169 towns (including zeros)
"""
import sys
from pathlib import Path
import pandas as pd
import geopandas as gpd
from typing import Dict, Optional
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent / "backend"))

# Complete list of all 169 Connecticut towns (standardized names)
ALL_169_CT_TOWNS = [
    "Andover", "Ansonia", "Ashford", "Avon", "Barkhamsted", "Beacon Falls",
    "Berlin", "Bethany", "Bethel", "Bethlehem", "Bloomfield", "Bolton",
    "Bozrah", "Branford", "Bridgeport", "Bridgewater", "Bristol", "Brookfield",
    "Brooklyn", "Burlington", "Canaan", "Canterbury", "Canton", "Chaplin",
    "Cheshire", "Chester", "Clinton", "Colchester", "Colebrook", "Columbia",
    "Cornwall", "Coventry", "Cromwell", "Danbury", "Darien", "Deep River",
    "Derby", "Durham", "East Granby", "East Haddam", "East Hampton", "East Hartford",
    "East Haven", "East Lyme", "East Windsor", "Eastford", "Easton", "Ellington",
    "Enfield", "Essex", "Fairfield", "Farmington", "Franklin", "Glastonbury",
    "Goshen", "Granby", "Greenwich", "Griswold", "Groton", "Guilford",
    "Haddam", "Hamden", "Hampton", "Hartford", "Hartland", "Harwinton",
    "Hebron", "Kent", "Killingly", "Killingworth", "Lebanon", "Ledyard",
    "Lisbon", "Litchfield", "Lyme", "Madison", "Manchester", "Mansfield",
    "Marlborough", "Meriden", "Middlebury", "Middlefield", "Middletown", "Milford",
    "Monroe", "Montville", "Morris", "Naugatuck", "New Britain", "New Canaan",
    "New Fairfield", "New Hartford", "New Haven", "New London", "New Milford",
    "Newington", "Newtown", "Norfolk", "North Branford", "North Canaan", "North Haven",
    "North Stonington", "Norwalk", "Norwich", "Old Lyme", "Old Saybrook", "Orange",
    "Oxford", "Plainfield", "Plainville", "Plymouth", "Pomfret", "Portland",
    "Preston", "Prospect", "Putnam", "Redding", "Ridgefield", "Rocky Hill",
    "Roxbury", "Salem", "Salisbury", "Scotland", "Seymour", "Sharon",
    "Shelton", "Sherman", "Simsbury", "Somers", "South Windsor", "Southbury",
    "Southington", "Sprague", "Stafford", "Stamford", "Sterling", "Stonington",
    "Stratford", "Suffield", "Thomaston", "Thompson", "Tolland", "Torrington",
    "Trumbull", "Union", "Vernon", "Voluntown", "Wallingford", "Warren",
    "Washington", "Waterbury", "Waterford", "Watertown", "West Hartford", "West Haven",
    "Westbrook", "Weston", "Westport", "Wethersfield", "Willington", "Wilton",
    "Winchester", "Windham", "Windsor", "Windsor Locks", "Wolcott", "Woodbridge",
    "Woodbury", "Woodstock"
]

def normalize_town_name(name: str) -> str:
    """
    Normalize town name for matching (handle case, spacing variations, typos)
    Returns standardized name from ALL_169_CT_TOWNS if found, otherwise returns normalized version
    """
    if not name or pd.isna(name):
        return ""
    
    # Convert to string and strip whitespace and trailing underscores
    name = str(name).strip().rstrip('_')
    
    # Common typo corrections
    typo_corrections = {
        'woobridge': 'Woodbridge',
        'barkhamstead': 'Barkhamsted',
        'winsted': 'Winchester',  # Winsted is a village in Winchester
    }
    
    name_lower = name.lower()
    if name_lower in typo_corrections:
        return typo_corrections[name_lower]
    
    # Try exact match first (case-insensitive)
    for town in ALL_169_CT_TOWNS:
        if town.lower() == name_lower:
            return town
    
    # Try matching with normalized spacing (handle multiple spaces, etc.)
    normalized_input = ' '.join(name.split())
    normalized_input_lower = normalized_input.lower()
    for town in ALL_169_CT_TOWNS:
        if town.lower() == normalized_input_lower:
            return town
    
    # Try fuzzy matching for common variations (e.g., "New Fairfield_" -> "New Fairfield")
    # Remove trailing underscores and try again
    if normalized_input_lower.endswith('_'):
        normalized_input_lower = normalized_input_lower[:-1]
        for town in ALL_169_CT_TOWNS:
            if town.lower() == normalized_input_lower:
                return town
    
    # If no match found, return the normalized input (capitalize properly)
    return normalized_input.title()

def create_town_name_mapping(counts_dict: Dict[str, int]) -> Dict[str, int]:
    """
    Create a mapping from normalized town names to counts
    Maps all variations to the standard town names from ALL_169_CT_TOWNS
    """
    normalized_counts = {}
    for raw_name, count in counts_dict.items():
        if raw_name == '[NULL/EMPTY]':
            continue
        normalized_name = normalize_town_name(raw_name)
        if normalized_name:
            # If multiple variations map to same town, sum them
            if normalized_name in normalized_counts:
                normalized_counts[normalized_name] += count
            else:
                normalized_counts[normalized_name] = count
    return normalized_counts

def analyze_geodatabase(gdb_path: str) -> Dict[str, int]:
    """
    Count properties by town in the geodatabase
    Returns: {town_name: count} with normalized town names
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
    
    raw_town_counts = gdf['Town_Name'].value_counts().to_dict()
    
    # Normalize town names
    normalized_counts = create_town_name_mapping(raw_town_counts)
    
    print(f"Found {len(normalized_counts)} unique towns after normalization")
    if 'Bridgeport' in normalized_counts:
        print(f"Bridgeport count: {normalized_counts.get('Bridgeport', 0):,}")
    
    return normalized_counts

def analyze_cama_excel_files(data_dir: str) -> Dict[str, int]:
    """
    Count properties by town in CAMA Excel files
    Looks for files matching pattern: {Town}_CAMA_2025_CLEANED.xlsx
    Returns: {town_name: count} with normalized town names
    """
    print("\n" + "=" * 80)
    print("ANALYZING CAMA EXCEL FILES (POST DUPLICATE CLEAN)")
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
            raw_town_name = excel_file.stem.replace("_CAMA_2025_CLEANED", "")
            town_name = normalize_town_name(raw_town_name)
            
            if not town_name:
                print(f"  ⚠️  Could not normalize town name: {raw_town_name}")
                continue
            
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
    Returns: {town_name: count} with normalized town names
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
            raw_town_name = csv_file.stem.replace("_CAMA_2025", "")
            town_name = normalize_town_name(raw_town_name)
            
            if not town_name:
                print(f"  ⚠️  Could not normalize town name: {raw_town_name}")
                continue
            
            # Read CSV file
            df = pd.read_csv(csv_file, low_memory=False)
            count = len(df)
            town_counts[town_name] = count
            print(f"  {town_name:30s}: {count:6,} properties")
            
        except Exception as e:
            print(f"  ⚠️  Error reading {csv_file.name}: {e}")
    
    return town_counts

def generate_169_towns_report(
    gdb_counts: Dict[str, int],
    excel_counts: Dict[str, int],
    csv_counts: Dict[str, int],
    output_file: str
) -> pd.DataFrame:
    """
    Generate a comprehensive report for all 169 towns and save to Excel
    """
    print("\n" + "=" * 80)
    print("GENERATING REPORT FOR ALL 169 TOWNS")
    print("=" * 80)
    
    # Build report data for all 169 towns
    report_data = []
    missing_from_all = []
    
    for town in sorted(ALL_169_CT_TOWNS):
        gdb_count = gdb_counts.get(town, 0)
        excel_count = excel_counts.get(town, 0)
        csv_count = csv_counts.get(town, 0)
        total_count = gdb_count + excel_count + csv_count
        
        # Determine notes
        notes_parts = []
        if gdb_count == 0:
            notes_parts.append("No geodatabase data")
        if excel_count == 0:
            notes_parts.append("No Excel file")
        if csv_count == 0:
            notes_parts.append("No CSV file")
        
        notes = "; ".join(notes_parts) if notes_parts else ""
        
        if total_count == 0:
            missing_from_all.append(town)
        
        report_data.append({
            'Town': town,
            'Geodatabase_Count': gdb_count,
            'CSV_Count': csv_count,
            'Post_Duplicate_Excel_Count': excel_count,
            'Total_Count': total_count,
            'Notes': notes
        })
    
    # Create DataFrame
    df = pd.DataFrame(report_data)
    
    # Sort by town name alphabetically (already sorted)
    
    # Save to Excel with formatting
    print(f"\nSaving report to Excel: {output_file}")
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        # Main data sheet
        df.to_excel(writer, sheet_name='Town Data Counts', index=False)
        
        # Get workbook and worksheet for formatting
        workbook = writer.book
        worksheet = writer.sheets['Town Data Counts']
        
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
                'Total Towns (All 169)',
                'Towns with Geodatabase Data',
                'Towns with CSV Files',
                'Towns with Excel Files',
                'Towns Missing from All Sources',
                'Total Properties (Geodatabase)',
                'Total Properties (CSV)',
                'Total Properties (Post Duplicate Excel)',
                'Grand Total Properties',
            ],
            'Value': [
                len(ALL_169_CT_TOWNS),
                int((df['Geodatabase_Count'] > 0).sum()),
                int((df['CSV_Count'] > 0).sum()),
                int((df['Post_Duplicate_Excel_Count'] > 0).sum()),
                len(missing_from_all),
                int(df['Geodatabase_Count'].sum()),
                int(df['CSV_Count'].sum()),
                int(df['Post_Duplicate_Excel_Count'].sum()),
                int(df['Total_Count'].sum()),
            ]
        }
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name='Summary', index=False)
        
        # Format summary sheet
        summary_worksheet = writer.sheets['Summary']
        for column in summary_worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            summary_worksheet.column_dimensions[column_letter].width = adjusted_width
    
    print(f"✅ Excel report saved to: {output_file}")
    
    # Print summary statistics
    print("\n" + "=" * 80)
    print("SUMMARY STATISTICS")
    print("=" * 80)
    
    total_gdb = df['Geodatabase_Count'].sum()
    total_excel = df['Post_Duplicate_Excel_Count'].sum()
    total_csv = df['CSV_Count'].sum()
    total_all = df['Total_Count'].sum()
    
    towns_with_gdb = (df['Geodatabase_Count'] > 0).sum()
    towns_with_excel = (df['Post_Duplicate_Excel_Count'] > 0).sum()
    towns_with_csv = (df['CSV_Count'] > 0).sum()
    
    print(f"Total towns analyzed: {len(df)} (all 169 CT towns)")
    print(f"\nTowns with data:")
    print(f"  Towns with Geodatabase data: {towns_with_gdb}")
    print(f"  Towns with CSV files:        {towns_with_csv}")
    print(f"  Towns with Excel files:      {towns_with_excel}")
    print(f"  Towns missing from all:      {len(missing_from_all)}")
    
    if missing_from_all:
        print(f"\n⚠️  Towns missing from all sources ({len(missing_from_all)}):")
        for town in missing_from_all[:10]:
            print(f"    - {town}")
        if len(missing_from_all) > 10:
            print(f"    ... and {len(missing_from_all) - 10} more")
    
    print(f"\nTotal Properties:")
    print(f"  Geodatabase:        {total_gdb:,}")
    print(f"  CSV:                {total_csv:,}")
    print(f"  Post Duplicate Excel: {total_excel:,}")
    print(f"  Grand Total:        {total_all:,}")
    
    return df

def main():
    # Paths
    script_dir = Path(__file__).parent
    gdb_path = script_dir.parent / "2025 Parcel Layer.gdb"
    data_dir = Path("/Users/jacobmermelstein/Desktop/CT Data")
    
    # Output file in the same directory as script
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = script_dir / f"169_towns_data_count_{timestamp}.xlsx"
    
    print("=" * 80)
    print("169 CT TOWNS DATA COUNT ANALYSIS")
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
        
        # Generate report for all 169 towns
        df = generate_169_towns_report(gdb_counts, excel_counts, csv_counts, str(output_file))
        
        print("\n" + "=" * 80)
        print("✅ ANALYSIS COMPLETE")
        print("=" * 80)
        print(f"Excel report saved to: {output_file}")
        print(f"Report includes all {len(ALL_169_CT_TOWNS)} Connecticut towns")
        
    except Exception as e:
        print(f"\n❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    main()
