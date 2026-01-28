# Hybrid Analysis Approach Design

## Overview

This document defines how Python scripts, SQL queries, SQL query interface, and the interactive dashboard work together to provide comprehensive property ownership analysis capabilities.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    User Analysis Needs                       │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Quick      │    │   Standard   │    │   Complex    │
│   Query      │    │   Analysis   │    │   Analysis   │
│  (< 5 min)   │    │  (Common)    │    │  (Custom)    │
└──────────────┘    └──────────────┘    └──────────────┘
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ SQL Query    │    │ Interactive │    │   Python     │
│ Interface    │    │  Dashboard  │    │   Scripts    │
│              │    │             │    │              │
│ - Direct SQL │    │ - Pre-built │    │ - Full       │
│ - Results    │    │   analyses  │    │   flexibility│
│ - Export     │    │ - Charts    │    │ - Excel      │
│ - Save/Load  │    │ - Tables    │    │   formatting │
└──────────────┘    └──────────────┘    └──────────────┘
```

## Tool Responsibilities

### Python Scripts (`backend/scripts/analysis/`)

**Primary Role:** Complex, custom, formatted analyses

**Responsibilities:**
- ✅ Complex multi-step analysis
- ✅ Custom Excel formatting
- ✅ Combining multiple data sources
- ✅ Scheduled/automated reports
- ✅ One-time deep dives
- ✅ Complex aggregations (fuzzy matching, statistical analysis)

**When to Use:**
- Need specific Excel formatting
- Complex logic that's easier in Python
- One-time custom analysis
- Scheduled/automated reports
- Multi-step processing

**Examples:**
- Top owners by mailing address (with custom formatting)
- LLC analysis with detailed breakdowns
- Custom property type aggregations
- Weekly ownership reports

**Access:**
- Command line: `python backend/scripts/analysis/top_owners_by_address.py --municipality "Bridgeport"`
- Output: Excel files in `Analysis scripts/` directory

### SQL Query Interface (Proposed: `/query`)

**Primary Role:** Quick ad-hoc queries, team collaboration

**Responsibilities:**
- ✅ Quick data checks
- ✅ Testing hypotheses
- ✅ Data validation
- ✅ Debugging
- ✅ Team query sharing
- ✅ Export query results

**When to Use:**
- Quick question (< 5 minutes)
- Testing a query before building feature
- Need to share query with team
- Don't have TablePlus installed
- Want query history

**Examples:**
- "How many properties does owner 'Smith LLC' have?"
- "Show me all properties with missing owner data"
- "What's the average assessed value by town?"

**Access:**
- Web browser: Navigate to `/query`
- Enter SQL directly
- View results in table
- Export to CSV/Excel
- Save/load queries

### Interactive Dashboard (Proposed: `/analytics`)

**Primary Role:** Standard analyses with visual exploration

**Responsibilities:**
- ✅ Pre-built standard analyses
- ✅ Visual charts and graphs
- ✅ Interactive exploration
- ✅ Quick insights
- ✅ Non-technical user access

**When to Use:**
- Standard analysis (top owners, LLC breakdown)
- Need visual charts
- Non-technical users
- Quick insights without writing code
- Want to explore data interactively

**Examples:**
- "Show me top 20 owners in Bridgeport with a bar chart"
- "LLC vs non-LLC breakdown for Hartford"
- "Property type distribution in Torrington"

**Access:**
- Web browser: Navigate to `/analytics`
- Select analysis type
- Select town/municipality
- View charts and tables
- Export results

### SQL Queries (TablePlus)

**Primary Role:** Development and debugging

**Responsibilities:**
- ✅ Quick data checks during development
- ✅ Testing queries
- ✅ Debugging data issues
- ✅ Direct database access

**When to Use:**
- During development
- Quick local checks
- Testing before building features
- Direct database access needed

**Examples:**
- "Check if property exists"
- "Validate data quality"
- "Test query performance"

## Workflow Integration

### Scenario 1: Standard Analysis Request

**User:** "I need to see top 20 owners in Bridgeport"

**Workflow:**
1. User navigates to Dashboard (`/analytics`)
2. Selects "Top Owners by Mailing Address"
3. Selects "Bridgeport" from town dropdown
4. Sets limit to 20
5. Views bar chart and table
6. Exports to Excel if needed

**Tools Used:** Dashboard

### Scenario 2: Quick Data Check

**User:** "How many properties does 'Smith LLC' own?"

**Workflow:**
1. User navigates to SQL Query Interface (`/query`)
2. Enters SQL: `SELECT COUNT(*) FROM properties WHERE owner_name LIKE '%Smith LLC%'`
3. Views result
4. Optionally exports

**Tools Used:** SQL Query Interface

### Scenario 3: Complex Custom Analysis

**User:** "I need a formatted report showing all LLC owners with >5 properties, grouped by town, with specific Excel formatting"

**Workflow:**
1. User identifies this is complex/custom
2. Uses Python script template
3. Customizes script for specific requirements
4. Runs: `python backend/scripts/analysis/custom_llc_report.py`
5. Gets formatted Excel output

**Tools Used:** Python Script

### Scenario 4: Testing Before Building Feature

**Developer:** "I need to test a query before adding it to the dashboard"

**Workflow:**
1. Developer writes SQL query in TablePlus or SQL Interface
2. Tests query performance and results
3. Once validated, implements in dashboard or Python script

**Tools Used:** SQL Queries → Dashboard/Python Script

## Data Flow

### Python Scripts
```
Database → SQLAlchemy → Pandas DataFrame → Analysis → Excel Export
```

### SQL Query Interface
```
User Input (SQL) → Database → Results → Table Display → Export
```

### Interactive Dashboard
```
User Selection → API Endpoint → Database Query → Aggregation → 
Charts + Table → Export
```

## Integration Points

### Shared Database
All tools access the same PostgreSQL database:
- Python Scripts: SQLAlchemy ORM
- SQL Interface: Direct SQL
- Dashboard: FastAPI endpoints → SQLAlchemy

### Shared Utilities
- `analysis_utils.py`: Shared formatting, LLC detection, Excel export
- Can be imported by both Python scripts and potentially dashboard backend

### Export Formats
- Python Scripts: Excel (formatted)
- SQL Interface: CSV, Excel
- Dashboard: CSV, Excel

## User Guidance

### Decision Tree for Users

```
Need Analysis?
    │
    ├─ Is it a standard analysis? (top owners, LLC, property types)
    │   │
    │   ├─ Yes → Use Dashboard (/analytics)
    │   │
    │   └─ No → Continue
    │
    ├─ Is it a quick question? (< 5 minutes)
    │   │
    │   ├─ Yes → Use SQL Query Interface (/query)
    │   │
    │   └─ No → Continue
    │
    ├─ Need custom formatting or complex logic?
    │   │
    │   ├─ Yes → Use Python Script
    │   │
    │   └─ No → Use SQL Query Interface or Dashboard
    │
    └─ Need scheduled/automated?
        │
        ├─ Yes → Use Python Script (can be scheduled)
        │
        └─ No → Use appropriate tool above
```

## Implementation Phases

### Phase 1: Python Scripts ✅ (Complete)
- ✅ Reusable analysis functions
- ✅ Standardized Excel formatting
- ✅ Top owners by address/name
- ✅ LLC analysis
- ✅ Documentation

### Phase 2: SQL Query Interface (Next)
**Timeline:** 2-3 weeks
**Priority:** High

**Features:**
- SQL input field
- Results table with pagination
- Export to CSV/Excel
- Save/load queries
- Query history

**Why First:**
- Less development than dashboard
- High value for technical users
- Can test queries before building dashboard

### Phase 3: Interactive Dashboard (Later)
**Timeline:** 2-3 weeks
**Priority:** Medium

**Features:**
- Pre-built analyses (top owners, LLC)
- Visual charts
- Interactive exploration
- Export functionality

**Why Later:**
- More complex to build
- Python scripts handle complex cases
- SQL interface provides quick wins first

## Best Practices

### For Python Scripts
- ✅ Use `analysis_utils.py` for common functions
- ✅ Follow existing script patterns
- ✅ Include command-line arguments
- ✅ Generate formatted Excel output
- ✅ Document in README.md

### For SQL Queries
- ✅ Keep queries simple and readable
- ✅ Use indexes (municipality, owner_name, etc.)
- ✅ Limit result sets for performance
- ✅ Document complex queries

### For Dashboard
- ✅ Focus on standard analyses
- ✅ Provide visual charts
- ✅ Make it accessible to non-technical users
- ✅ Include export functionality
- ✅ Keep it simple (don't try to replace Python scripts)

## Conclusion

The hybrid approach provides:

- **Flexibility:** Python scripts for complex cases
- **Speed:** SQL interface for quick queries
- **Accessibility:** Dashboard for non-technical users
- **Power:** Each tool optimized for its use case

**Key Principle:** Use the right tool for the job. Don't try to make one tool do everything.
