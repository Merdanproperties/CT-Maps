# Property Ownership Analysis Tools - Quick Reference

## Overview

This is a quick reference guide for the property ownership analysis tools. For detailed information, see the other guides in this directory.

## Available Tools

### 1. Python Analysis Scripts ✅ (Available Now)

**Location:** `backend/scripts/analysis/`

**Quick Start:**
```bash
# Top owners by mailing address
python backend/scripts/analysis/top_owners_by_address.py --municipality "Bridgeport"

# Top owners by name
python backend/scripts/analysis/top_owners_by_name.py --municipality "Bridgeport"

# LLC analysis
python backend/scripts/analysis/llc_analysis.py --municipality "Bridgeport"
```

**Output:** Excel files in `Analysis scripts/` directory

**Best For:**
- Complex custom analyses
- Formatted Excel reports
- Scheduled/automated reports
- One-time deep dives

**Documentation:** `backend/scripts/analysis/README.md`

### 2. SQL Queries (TablePlus) ✅ (Available Now)

**Location:** `TABLEPLUS_QUERIES.sql`

**Quick Start:**
- Open TablePlus
- Connect to database
- Copy/paste queries from `TABLEPLUS_QUERIES.sql`

**Best For:**
- Quick data checks
- Testing hypotheses
- Debugging
- Development

### 3. SQL Query Interface (Proposed)

**Location:** Web app at `/query` (not yet implemented)

**Planned Features:**
- Direct SQL input
- Results table
- Export to CSV/Excel
- Save/load queries

**Best For:**
- Quick queries (like TablePlus)
- Team collaboration
- Sharing queries

**Status:** Recommended for Phase 2 implementation

### 4. Interactive Dashboard (Proposed)

**Location:** Web app at `/analytics` (not yet implemented)

**Planned Features:**
- Pre-built analyses (top owners, LLC)
- Visual charts
- Interactive exploration
- Export functionality

**Best For:**
- Standard analyses
- Visual exploration
- Non-technical users

**Status:** Recommended for Phase 3 implementation

## Quick Decision Guide

**Need a standard analysis?** (top owners, LLC breakdown)
→ Use Dashboard (when built) or Python script

**Quick question?** (< 5 minutes)
→ Use SQL Query Interface (when built) or TablePlus

**Complex/custom analysis?**
→ Use Python Script

**Need formatted Excel?**
→ Use Python Script

**Need visual charts?**
→ Use Dashboard (when built)

## Implementation Status

### ✅ Phase 1: Python Scripts (Complete)
- Reusable analysis functions
- Standardized Excel formatting
- Top owners by address/name
- LLC analysis
- Documentation

### 📋 Phase 2: SQL Query Interface (Recommended Next)
- Timeline: 2-3 weeks
- Priority: High
- Value: Makes SQL queries more accessible

### 📋 Phase 3: Interactive Dashboard (Later)
- Timeline: 2-3 weeks
- Priority: Medium
- Value: Best UX for standard analyses

## Related Documentation

- **Analysis Scripts README:** `backend/scripts/analysis/README.md`
- **Tools Evaluation:** `Documentation/guides/ANALYSIS_TOOLS_EVALUATION.md`
- **Feature Prioritization:** `Documentation/guides/DASHBOARD_FEATURE_PRIORITIZATION.md`
- **Hybrid Approach Design:** `Documentation/guides/HYBRID_APPROACH_DESIGN.md`

## Getting Help

- **Python Scripts:** See `backend/scripts/analysis/README.md`
- **SQL Queries:** See `TABLEPLUS_QUERIES.sql` for examples
- **General Questions:** See evaluation and design documents
