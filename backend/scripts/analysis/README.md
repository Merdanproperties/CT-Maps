# Property Ownership Analysis Scripts

This directory contains reusable Python scripts for analyzing property ownership data from the CT Properties database.

## Available Analyses

### 1. Top Owners by Mailing Address
**Script:** `top_owners_by_address.py`

Groups properties by owner name + mailing address (owner_address, owner_city, owner_state) to identify owners with multiple properties at the same mailing address.

**Usage:**
```bash
# Analyze all towns
python backend/scripts/analysis/top_owners_by_address.py

# Analyze specific town
python backend/scripts/analysis/top_owners_by_address.py --municipality "Bridgeport"

# Customize top N and minimum properties
python backend/scripts/analysis/top_owners_by_address.py --municipality "Bridgeport" --top-n 50 --min-properties 2
```

**Output:** Excel file with sheets per town showing top owners grouped by mailing address.

### 2. Top Owners by Name
**Script:** `top_owners_by_name.py`

Groups properties by owner name only (regardless of mailing address) to identify owners with multiple properties across different addresses.

**Usage:**
```bash
# Analyze all towns
python backend/scripts/analysis/top_owners_by_name.py

# Analyze specific town
python backend/scripts/analysis/top_owners_by_name.py --municipality "Bridgeport"
```

**Output:** Excel file with sheets per town showing top owners grouped by name.

### 3. LLC Analysis
**Script:** `llc_analysis.py`

Identifies properties owned by LLCs and other business entities, providing breakdown by town showing LLC vs non-LLC ownership.

**Usage:**
```bash
# Analyze all towns
python backend/scripts/analysis/llc_analysis.py

# Analyze specific town
python backend/scripts/analysis/llc_analysis.py --municipality "Bridgeport"
```

**Output:** Excel file with LLC breakdown per town, including top LLC owners.

## Utility Functions

The `analysis_utils.py` module provides:

- **Excel Export:** Standardized formatting with headers, borders, auto-width adjustment
- **LLC Detection:** Detects LLC, Inc., Corp., Trust, and other business entities
- **Database Access:** Helper functions to load properties from database
- **Formatting:** Currency and number formatting utilities
- **Summary Sheets:** Create summary metadata sheets

## Output Format

All scripts generate Excel files with:
- **Formatted headers:** Blue background, white text, bold
- **Auto-adjusted column widths**
- **Number formatting:** Currency and percentages
- **Summary sheets:** Metadata and overall statistics
- **Multiple sheets:** One per town (for all-towns analysis)

## Output Location

Excel files are saved to: `Analysis scripts/` directory at the project root.

Files are named with timestamps:
- `2025_TOP_OWNERS_BY_ADDRESS_PER_TOWN_YYYYMMDD_HHMMSS.xlsx`
- `2025_TOP_OWNERS_BY_NAME_PER_TOWN_YYYYMMDD_HHMMSS.xlsx`
- `2025_LLC_ANALYSIS_BY_TOWN_YYYYMMDD_HHMMSS.xlsx`

## Requirements

- Python 3.8+
- pandas
- openpyxl
- sqlalchemy
- Database connection configured in `.env`

## Extending

To create a new analysis script:

1. Import utilities from `analysis_utils.py`
2. Use `load_properties_from_db()` to get data
3. Process and aggregate data with pandas
4. Use `export_to_excel()` to generate formatted output
5. Follow the pattern of existing scripts for consistency

## Examples

### Basic Analysis
```python
from scripts.analysis.analysis_utils import (
    get_database_session,
    load_properties_from_db,
    export_to_excel
)

db = get_database_session()
df = load_properties_from_db(municipality="Bridgeport", db_session=db)

# Your analysis logic here
results = {
    'Sheet Name': your_dataframe,
    'Summary': summary_dataframe
}

export_to_excel(results, output_file)
```
