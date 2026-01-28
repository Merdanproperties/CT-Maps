# Analysis Tools Evaluation & Design

## Overview

This document evaluates different approaches for property ownership analysis and provides recommendations for when to use each tool.

## Current Tools

### 1. Python Analysis Scripts
**Location:** `backend/scripts/analysis/`

**Capabilities:**
- Complex aggregations and multi-step analysis
- Full Excel formatting control
- Can process entire database
- Reproducible, version-controlled scripts
- Can combine multiple data sources

**Best For:**
- Complex custom analyses
- Formatted reports with specific requirements
- One-time deep dives
- Scheduled/automated reports
- Multi-step analysis pipelines

**Examples:**
- Top owners by mailing address per town
- LLC analysis with detailed breakdowns
- Custom property type aggregations

### 2. SQL Queries (TablePlus)
**Location:** `TABLEPLUS_QUERIES.sql`

**Capabilities:**
- Fastest iteration
- Full SQL power
- Immediate results
- Direct database access

**Best For:**
- Quick ad-hoc questions
- Testing hypotheses
- Data validation
- Debugging data issues
- Query development before building features

**Examples:**
- "How many properties in Bridgeport?"
- "What's the average assessed value?"
- "Show me properties with missing owner data"

### 3. Web App Export
**Location:** `backend/api/routes/export.py`

**Capabilities:**
- Export filtered property lists
- CSV and Excel formats
- Based on UI filters

**Best For:**
- Exporting search results
- Sharing filtered property lists
- Quick exports from map/search views

## Recommended Additions

### 4. SQL Query Interface (Proposed)
**Location:** New page in web app (`/query`)

**Design:**
- Direct SQL input field
- Results table with pagination
- Export to CSV/Excel
- Save/load common queries
- Query history

**Benefits:**
- More accessible than TablePlus
- Can share queries with team
- Export functionality built-in
- No need to install database client

**Best For:**
- Quick queries (like TablePlus)
- Team collaboration
- Non-technical users who know SQL basics

**Implementation Priority:** Medium

### 5. Interactive Dashboard (Proposed)
**Location:** New page in web app (`/analytics`)

**Design:**
- Pre-built analyses (top owners, LLC breakdown)
- Visual charts and graphs
- Interactive exploration
- Customizable queries (limited)

**Benefits:**
- Best user experience
- No code required
- Visual insights
- Shareable URLs

**Best For:**
- Standard, frequently-used analyses
- Visual exploration
- Non-technical users
- Quick insights

**Implementation Priority:** Low (after SQL interface)

## Tool Selection Guide

### When to Use Python Scripts

✅ **Use Python Scripts When:**
- Need complex multi-step analysis
- Require specific Excel formatting
- Combining multiple data sources
- Creating one-time custom reports
- Need to schedule/automate analysis
- Analysis logic is complex (regex, fuzzy matching, etc.)

**Example:** "Generate a report showing all LLC owners with >5 properties, grouped by town, with formatted Excel output including charts"

### When to Use SQL Queries

✅ **Use SQL Queries When:**
- Quick data check
- Testing a hypothesis
- Validating data
- Debugging issues
- Developing queries before building features
- Simple aggregations

**Example:** "How many properties does owner 'Smith LLC' have across all towns?"

### When to Use SQL Query Interface (Proposed)

✅ **Use SQL Query Interface When:**
- Need to share queries with team
- Want export functionality
- Don't have TablePlus installed
- Need query history
- Quick queries (same as SQL, but in browser)

**Example:** Same as SQL queries, but when you want to share or export results

### When to Use Interactive Dashboard (Proposed)

✅ **Use Dashboard When:**
- Standard analysis (top owners, LLC breakdown)
- Need visual charts
- Non-technical users
- Quick insights without writing code
- Want to explore data interactively

**Example:** "Show me top 20 owners in Bridgeport with a bar chart"

### When to Use Web App Export

✅ **Use Web App Export When:**
- Exporting search results from map
- Sharing filtered property lists
- Quick CSV/Excel export

**Example:** "Export all vacant properties in Hartford to Excel"

## Feature Prioritization

### Phase 1: Python Scripts (✅ Complete)
- ✅ Reusable analysis functions
- ✅ Standardized Excel formatting
- ✅ Top owners by address/name
- ✅ LLC analysis

### Phase 2: SQL Query Interface (Recommended Next)
**Effort:** 2-3 weeks
**Value:** High - makes SQL queries more accessible

**Features:**
- SQL input field
- Results table
- Export to CSV/Excel
- Save/load queries
- Query history

**Why First:**
- Less development than full dashboard
- High value for technical users
- Can be used to test queries before building dashboard features

### Phase 3: Interactive Dashboard (Later)
**Effort:** 2-3 weeks
**Value:** High for non-technical users, medium for technical users

**Features:**
- Pre-built analyses (top owners, LLC)
- Visual charts
- Interactive exploration
- Customizable queries (limited)

**Why Later:**
- More complex to build
- Python scripts already handle complex cases
- SQL interface provides quick wins first

## Hybrid Approach Design

### Workflow Integration

```
┌─────────────────────────────────────────────────────────┐
│  User Needs Analysis                                    │
└─────────────────────────────────────────────────────────┘
                    │
        ┌───────────┴───────────┐
        │                       │
        ▼                       ▼
┌───────────────┐      ┌───────────────┐
│ Quick Query?  │      │ Complex?      │
│ (< 5 min)     │      │ (> 5 min)     │
└───────────────┘      └───────────────┘
        │                       │
        ▼                       ▼
┌───────────────┐      ┌───────────────┐
│ SQL Interface │      │ Python Script  │
│ or Dashboard  │      │                │
└───────────────┘      └───────────────┘
```

### Decision Tree

1. **Is it a standard analysis?** (top owners, LLC breakdown)
   - Yes → Use Dashboard (when built) or Python script
   - No → Continue

2. **Is it a quick question?** (< 5 minutes to answer)
   - Yes → Use SQL Query Interface or TablePlus
   - No → Continue

3. **Is it complex?** (multi-step, custom logic, formatting)
   - Yes → Use Python Script
   - No → Use SQL Query Interface

4. **Need formatted Excel output?**
   - Yes → Use Python Script
   - No → Use SQL Query Interface or Dashboard

## Implementation Recommendations

### Immediate (Done)
- ✅ Python analysis scripts with standardized formatting
- ✅ Documentation and examples

### Short-term (Next 1-2 months)
- SQL Query Interface in web app
- Save/load query functionality
- Export from query results

### Long-term (3+ months)
- Interactive dashboard
- Pre-built analyses
- Visual charts
- Customizable queries

## Conclusion

**Best approach:** Hybrid using all tools strategically

- **Python Scripts:** Complex, custom, formatted reports
- **SQL Queries:** Quick questions, testing, debugging
- **SQL Interface:** Accessible SQL queries, team sharing
- **Dashboard:** Standard analyses, visual exploration, non-technical users

Each tool serves different needs and complements the others.
