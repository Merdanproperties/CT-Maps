# Automated CAMA Verification System

## Overview

This automated verification system ensures **0% mismatch rate** for all towns in the database. It automatically verifies CAMA data accuracy before and after imports, protects existing towns from data corruption, and works for any municipality (current and future).

## Key Features

- **0% Mismatch Tolerance**: Any mismatch is a failure - no exceptions
- **Automated Verification**: Runs before/after every import
- **Protects Existing Towns**: Verifies no corruption during imports
- **Generic & Reusable**: Works for any town (current and future)
- **Continuous Monitoring**: Can run on-demand or scheduled
- **Fail-Fast**: Stops immediately if mismatches found
- **Auto-Fix**: Attempts to fix mismatches automatically

## System Components

### 1. Generic CAMA Verification Module (`cama_verification.py`)
- Verifies CAMA data for any municipality
- Enforces 0% mismatch tolerance
- Functions: `verify_cama_data()`, `find_mismatches()`, `check_completeness()`

### 2. Generic CAMA Update Module (`cama_update.py`)
- Updates properties from cleaned Excel files
- Ensures cleaned Excel is single source of truth
- Functions: `update_all_cama_from_cleaned_excel()`, `fix_mismatches()`

### 3. Automated Verification System (`automated_cama_verification.py`)
- Main verification system
- Verifies all towns or specific town
- Pre/post-import verification
- Re-verification to ensure no corruption

### 4. Standard Import Workflow (`import_with_verification.py`)
- Complete 8-step import workflow
- Built-in verification at every step
- Protects existing towns automatically

### 5. Continuous Monitoring (`monitor_cama_data.py`)
- On-demand or scheduled monitoring
- Daily report generation
- Alerts if mismatch rate > 0%

## Quick Start

### Verify All Towns
```bash
cd backend
python -m scripts.data_import.verification.automated_cama_verification --all
```

### Verify Specific Town
```bash
python -m scripts.data_import.verification.automated_cama_verification --municipality Bridgeport
```

### Verify Before Importing New Town
```bash
python -m scripts.data_import.verification.automated_cama_verification --before-import NewTown
```

### Standard Import Workflow (Recommended)
```bash
python -m scripts.data_import.import_with_verification NewTown
```

This automatically:
1. Verifies all existing towns (0% mismatch required)
2. Imports new town properties
3. Updates CAMA data from cleaned Excel
4. Verifies new town (0% mismatch required)
5. Re-verifies all existing towns (no corruption)
6. Fixes any mismatches
7. Final verification (all towns)
8. Generates report

### Monitor All Towns
```bash
python -m scripts.data_import.monitor_cama_data --all
```

### Update CAMA Data for Town
```bash
python -m scripts.data_import.cama_tools.cama_update --municipality Bridgeport
```

## File Structure

```
backend/scripts/data_import/
├── cama_verification.py              # Generic verification module
├── cama_update.py                    # Generic update module
├── automated_cama_verification.py     # Main verification system
├── import_with_verification.py        # Standard import workflow
├── monitor_cama_data.py              # Continuous monitoring
├── IMPORT_CHECKLIST.md               # Standard import checklist
├── LESSONS_LEARNED_TORRINGTON.md     # Lessons learned (updated)
└── VERIFICATION_SYSTEM_README.md     # This file
```

## Verification Workflow

```
Before Import:
  1. Verify all existing towns (0% mismatch required)
  2. If mismatches found → Fix before proceeding
  3. Load cleaned Excel for new town
  4. Verify cleaned Excel file integrity
  
During Import:
  1. Import properties from geodatabase
  2. Import/update CAMA from cleaned Excel
  3. Verify each batch (0% mismatch)
  
After Import:
  1. Verify new town (0% mismatch required)
  2. Re-verify all existing towns (ensure no corruption)
  3. If any mismatches → Fix immediately (0% tolerance)
  4. Final verification: All towns (0% mismatch)
  5. Generate comprehensive report
```

## 0% Mismatch Tolerance Policy

- **Zero Tolerance**: Any mismatch is a failure
- **Fail-Fast**: Stop import if mismatches found
- **Auto-Fix**: Attempt to fix mismatches automatically
- **Manual Review**: If auto-fix fails, require manual review
- **No Proceed**: Cannot proceed with import if mismatches exist
- **Protection**: Existing towns must remain at 0% mismatch

## Verification Metrics

For each town, the system verifies:
- **Match Rate**: 100% of properties matched to cleaned Excel
- **Data Accuracy**: 100% of CAMA fields match cleaned Excel
- **Completeness**: All required fields populated
- **Data Source**: 100% from cleaned Excel (single source of truth)
- **Mismatch Rate**: 0% (zero tolerance)

## Integration Points

- **Import Scripts**: Must call verification before/after
- **Update Scripts**: Must verify after updates
- **Monitoring**: Runs continuously or on-demand
- **CI/CD**: Can be integrated into deployment pipeline
- **Alerts**: Notify if mismatch rate > 0%

## Data Source Priority

1. **Cleaned Excel** (`{TOWN}_CAMA_2025_CLEANED.xlsx`) - Single source of truth
2. **CSV** (`{TOWN}_CAMA_2025.csv`) - Supplement only
3. **Existing database value** - Keep only if cleaned Excel doesn't have it

## Common Commands

### Verify All Towns
```bash
python -m scripts.data_import.verification.automated_cama_verification --all
```

### Verify Specific Town
```bash
python -m scripts.data_import.verification.automated_cama_verification --municipality <TOWN>
```

### Verify Before Import
```bash
python -m scripts.data_import.verification.automated_cama_verification --before-import <NEW_TOWN>
```

### Verify After Import
```bash
python -m scripts.data_import.verification.automated_cama_verification --after-import <NEW_TOWN>
```

### Monitor All Towns
```bash
python -m scripts.data_import.monitor_cama_data --all
```

### Update CAMA Data
```bash
python -m scripts.data_import.cama_tools.cama_update --municipality <TOWN>
```

### Standard Import (Recommended)
```bash
python -m scripts.data_import.import_with_verification <TOWN>
```

## Success Criteria

An import is only considered successful when:
- ✅ All existing towns verified with 0% mismatch rate (pre-import)
- ✅ New town properties imported successfully
- ✅ New town CAMA data updated from cleaned Excel
- ✅ New town verified with 0% mismatch rate (post-import)
- ✅ All existing towns re-verified with 0% mismatch rate (no corruption)
- ✅ Final verification: All towns have 0% mismatch rate
- ✅ Comprehensive report generated

**If any step fails, the import is NOT complete and must be fixed before proceeding.**

## Troubleshooting

### Verification Fails
1. Check if cleaned Excel file exists: `CT Data/2025 Post Duplicate Clean/{TOWN}_CAMA_2025_CLEANED.xlsx`
2. Run update: `python -m scripts.data_import.cama_tools.cama_update --municipality <TOWN>`
3. Re-verify: `python -m scripts.data_import.verification.automated_cama_verification --municipality <TOWN>`

### Import Fails
1. Check pre-import verification: All existing towns must have 0% mismatch
2. Fix any existing town issues first
3. Then proceed with new town import

### Mismatches Found
1. System will attempt auto-fix
2. If auto-fix fails, review mismatches manually
3. Update cleaned Excel file if needed
4. Re-run update and verification

## Best Practices

1. **Always use standard import workflow** - Never skip verification steps
2. **Verify before importing** - Ensure existing towns are at 0% mismatch
3. **Verify after importing** - Ensure new town and existing towns are at 0% mismatch
4. **Monitor regularly** - Run monitoring script daily or weekly
5. **Document issues** - Update lessons learned document with any new insights
6. **No shortcuts** - Follow the complete process for every import

## Support

For questions or issues:
1. Check `IMPORT_CHECKLIST.md` for standard procedures
2. Review `LESSONS_LEARNED_TORRINGTON.md` for common issues
3. Check verification reports for specific errors
4. Review logs for detailed error messages
