# Standard Import Checklist

**CRITICAL: 0% Mismatch Tolerance - All steps must pass**

This checklist must be followed for every town import to ensure data integrity and maintain 0% mismatch rate across all towns.

## Pre-Import Verification

- [ ] **Verify all existing towns** (0% mismatch required)
  - Run: `python -m scripts.data_import.verification.automated_cama_verification --before-import <NEW_TOWN>`
  - All existing towns must have 0% mismatch rate
  - Cannot proceed if any existing town has mismatches

- [ ] **Load cleaned Excel file** (single source of truth)
  - File location: `CT Data/2025 Post Duplicate Clean/{TOWN}_CAMA_2025_CLEANED.xlsx`
  - Verify file exists and is readable
  - This is the ONLY source for CAMA data

- [ ] **Load CSV file** (supplement only)
  - File location: `CT Data/2025 Parcel Collection/{TOWN}_CAMA_2025.csv`
  - CSV is ONLY for supplementing fields missing in cleaned Excel
  - Never use CSV as primary source

## Import Process

- [ ] **Import properties from geodatabase**
  - Import property geometries and basic information
  - Ensure all properties have valid geometries
  - Check for duplicates before inserting

- [ ] **Match and combine** (cleaned Excel primary)
  - Match cleaned Excel records to database properties
  - Use multiple matching strategies (parcel ID, normalized address)
  - Cleaned Excel data takes priority over CSV

- [ ] **Import/update CAMA data**
  - Update ALL properties with CAMA data from cleaned Excel
  - Use CSV only to supplement fields missing in cleaned Excel
  - Every property must get data from cleaned Excel file

## Post-Import Verification

- [ ] **Verify new town** (0% mismatch required)
  - Run: `python -m scripts.data_import.verification.automated_cama_verification --municipality <TOWN>`
  - New town must have 0% mismatch rate
  - If mismatches found, fix immediately

- [ ] **Re-verify all existing towns** (ensure no corruption)
  - Run: `python -m scripts.data_import.verification.automated_cama_verification --all`
  - All existing towns must still have 0% mismatch rate
  - If any town has mismatches, data corruption detected

- [ ] **Fix any mismatches** (0% tolerance - fail if can't fix)
  - Run: `python -m scripts.data_import.cama_update --municipality <TOWN>`
  - Attempt to fix mismatches automatically
  - If auto-fix fails, require manual review
  - Cannot proceed if mismatches exist

- [ ] **Final verification: All towns** (0% mismatch required)
  - Run: `python -m scripts.data_import.verification.automated_cama_verification --all`
  - All towns must have 0% mismatch rate
  - Import is only complete when all towns pass verification

## Reporting and Documentation

- [ ] **Generate comprehensive report**
  - Report includes:
    - Total properties imported
    - Properties updated
    - Fields updated
    - Verification results for all towns
    - Any issues or warnings

- [ ] **Document lessons learned**
  - Update `LESSONS_LEARNED.md` with any new insights
  - Document any issues encountered
  - Document any process improvements

## Automated Workflow

For convenience, use the standard import workflow which automates all steps:

```bash
python -m scripts.data_import.import_with_verification <TOWN>
```

This workflow:
- Automatically performs all verification steps
- Protects existing towns from data corruption
- Ensures 0% mismatch rate for all towns
- Fails fast if any step fails

## Verification Commands

### Verify all towns
```bash
python -m scripts.data_import.verification.automated_cama_verification --all
```

### Verify specific town
```bash
python -m scripts.data_import.verification.automated_cama_verification --municipality <TOWN>
```

### Verify before import
```bash
python -m scripts.data_import.verification.automated_cama_verification --before-import <NEW_TOWN>
```

### Verify after import
```bash
python -m scripts.data_import.verification.automated_cama_verification --after-import <NEW_TOWN>
```

### Monitor all towns
```bash
python -m scripts.data_import.monitor_cama_data --all
```

### Update CAMA data
```bash
python -m scripts.data_import.cama_update --municipality <TOWN>
```

## Critical Rules

1. **0% Mismatch Tolerance**: Any mismatch is a failure - no exceptions
2. **Cleaned Excel is Single Source of Truth**: Never use other sources for primary data
3. **Protect Existing Towns**: Always verify existing towns before and after imports
4. **Fail-Fast**: Stop immediately if mismatches found
5. **No Shortcuts**: Follow the complete process for every import
6. **Verify Everything**: Never assume data is correct without verification

## Success Criteria

An import is only considered successful when:
- ✅ All existing towns verified with 0% mismatch rate (pre-import)
- ✅ New town properties imported successfully
- ✅ New town CAMA data updated from cleaned Excel
- ✅ New town verified with 0% mismatch rate (post-import)
- ✅ All existing towns re-verified with 0% mismatch rate (no corruption)
- ✅ Final verification: All towns have 0% mismatch rate
- ✅ Comprehensive report generated
- ✅ Lessons learned documented

**If any step fails, the import is NOT complete and must be fixed before proceeding.**
