"""
Analyze which towns are missing Location data from their Excel files
Reads all Excel files in "Excel geodatabase all towns" folder and analyzes Location column
Outputs analysis report to the same folder
"""
import sys
from pathlib import Path
import pandas as pd
from datetime import datetime

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False
    def tqdm(iterable, desc="", unit=""):
        return iterable

def analyze_missing_locations():
    """
    Analyze Location data in all town Excel files
    """
    print("=" * 80)
    print("ANALYZING MISSING LOCATION DATA BY TOWN")
    print("=" * 80)
    
    # Get script directory and Excel folder
    script_dir = Path(__file__).parent
    excel_dir = script_dir / "Excel geodatabase all towns"
    
    if not excel_dir.exists():
        raise FileNotFoundError(f"Excel folder not found: {excel_dir}")
    
    print(f"\n📁 Excel folder: {excel_dir}")
    
    # Get all Excel files
    excel_files = list(excel_dir.glob("*.xlsx"))
    print(f"📊 Found {len(excel_files):,} Excel files to analyze")
    
    if len(excel_files) == 0:
        print("❌ No Excel files found!")
        return
    
    # Analyze each file
    results = []
    failed_files = []
    
    print("\n🔍 Analyzing files...")
    for excel_file in tqdm(excel_files, desc="Processing", unit="file"):
        try:
            # Extract town name from filename
            town_name = excel_file.stem.replace('_', ' ')
            
            # Read Excel file
            df = pd.read_excel(excel_file, engine='openpyxl')
            
            total_parcels = len(df)
            
            # Check for Location column (case-insensitive)
            location_col = None
            for col in df.columns:
                if col.lower() == 'location':
                    location_col = col
                    break
            
            if location_col is None:
                # No Location column found
                results.append({
                    'Town': town_name,
                    'Total_Parcels': total_parcels,
                    'With_Location': 0,
                    'Missing_Location': total_parcels,
                    'Location_Percentage': 0.0,
                    'Status': '❌ No Location Column'
                })
                continue
            
            # Analyze Location data
            location_data = df[location_col]
            
            # Count non-null, non-empty Location values
            # Consider empty strings, 'None', 'nan', etc. as missing
            has_location = (
                location_data.notna() & 
                (location_data.astype(str).str.strip() != '') &
                (location_data.astype(str).str.strip().str.lower() != 'none') &
                (location_data.astype(str).str.strip().str.lower() != 'nan')
            )
            
            with_location = has_location.sum()
            missing_location = total_parcels - with_location
            location_percentage = (with_location / total_parcels * 100) if total_parcels > 0 else 0
            
            # Categorize status
            if location_percentage >= 90:
                status = '✅ Excellent (90%+)'
            elif location_percentage >= 50:
                status = '⚠️  Partial (50-90%)'
            elif location_percentage > 0:
                status = '⚠️  Few Locations (<50%)'
            else:
                status = '❌ No Locations (0%)'
            
            results.append({
                'Town': town_name,
                'Total_Parcels': total_parcels,
                'With_Location': with_location,
                'Missing_Location': missing_location,
                'Location_Percentage': round(location_percentage, 2),
                'Status': status
            })
            
        except Exception as e:
            print(f"\n⚠️  Error processing {excel_file.name}: {e}")
            failed_files.append({
                'Town': excel_file.stem,
                'Error': str(e)
            })
            continue
    
    # Create results DataFrame
    results_df = pd.DataFrame(results)
    
    # Sort by location percentage (ascending - worst first)
    results_df = results_df.sort_values('Location_Percentage', ascending=True)
    
    # Print summary
    print("\n" + "=" * 80)
    print("ANALYSIS SUMMARY")
    print("=" * 80)
    
    excellent = results_df[results_df['Location_Percentage'] >= 90]
    partial = results_df[(results_df['Location_Percentage'] >= 50) & (results_df['Location_Percentage'] < 90)]
    few = results_df[(results_df['Location_Percentage'] > 0) & (results_df['Location_Percentage'] < 50)]
    none = results_df[results_df['Location_Percentage'] == 0]
    
    print(f"\n✅ Excellent (90%+): {len(excellent)} towns")
    print(f"⚠️  Partial (50-90%): {len(partial)} towns")
    print(f"⚠️  Few Locations (<50%): {len(few)} towns")
    print(f"❌ No Locations (0%): {len(none)} towns")
    print(f"\nTotal towns analyzed: {len(results_df)}")
    
    if len(failed_files) > 0:
        print(f"\n⚠️  Failed to process: {len(failed_files)} files")
    
    # Calculate totals
    total_parcels_all = results_df['Total_Parcels'].sum()
    total_with_location = results_df['With_Location'].sum()
    total_missing_location = results_df['Missing_Location'].sum()
    overall_percentage = (total_with_location / total_parcels_all * 100) if total_parcels_all > 0 else 0
    
    print(f"\nOverall Statistics:")
    print(f"  Total Parcels: {total_parcels_all:,}")
    print(f"  With Location: {total_with_location:,} ({overall_percentage:.2f}%)")
    print(f"  Missing Location: {total_missing_location:,} ({100-overall_percentage:.2f}%)")
    
    # Save to Excel
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = excel_dir / f"Location_Analysis_Report_{timestamp}.xlsx"
    
    print(f"\n📝 Saving analysis report...")
    print(f"   File: {output_file}")
    
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        # Main results sheet (sorted by worst first)
        results_df.to_excel(writer, sheet_name='All Towns Analysis', index=False)
        
        # Summary sheet
        summary_data = {
            'Category': [
                'Excellent (90%+)',
                'Partial (50-90%)',
                'Few Locations (<50%)',
                'No Locations (0%)',
                'Total Towns'
            ],
            'Count': [
                len(excellent),
                len(partial),
                len(few),
                len(none),
                len(results_df)
            ]
        }
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name='Summary', index=False)
        
        # Towns with missing locations (sorted by missing count)
        missing_towns = results_df[results_df['Missing_Location'] > 0].copy()
        missing_towns = missing_towns.sort_values('Missing_Location', ascending=False)
        missing_towns.to_excel(writer, sheet_name='Towns with Missing Locations', index=False)
        
        # Towns with no locations
        no_location_towns = results_df[results_df['Location_Percentage'] == 0].copy()
        if len(no_location_towns) > 0:
            no_location_towns.to_excel(writer, sheet_name='Towns with No Locations', index=False)
        
        # Auto-adjust column widths for all sheets
        for sheet_name in writer.sheets:
            worksheet = writer.sheets[sheet_name]
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
    
    print(f"\n✅ Analysis complete!")
    print(f"   Report saved to: {output_file}")
    
    # Print top 10 towns with most missing locations
    if len(missing_towns) > 0:
        print(f"\n📊 Top 10 Towns with Most Missing Locations:")
        print("-" * 80)
        for idx, row in missing_towns.head(10).iterrows():
            print(f"  {row['Town']:30s} - {row['Missing_Location']:6,} missing ({row['Location_Percentage']:5.2f}% have location)")
    
    return output_file

if __name__ == "__main__":
    try:
        analyze_missing_locations()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
