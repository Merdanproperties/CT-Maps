# Dashboard Feature Prioritization

## Overview

This document identifies which analyses should be implemented in the interactive dashboard vs which should remain as Python scripts.

## Analysis Classification

### Standard Analyses (Dashboard Candidates)

These are frequently-used, well-defined analyses that benefit from visual presentation:

#### 1. Top Owners by Mailing Address ✅ Dashboard
**Complexity:** Low
**Frequency:** High
**Visual Value:** High (bar charts)
**Python Script:** `top_owners_by_address.py`

**Dashboard Features:**
- Town selector dropdown
- Top N selector (10, 20, 50, 100)
- Bar chart: Top owners by property count
- Bar chart: Top owners by total assessed value
- Table: Detailed owner list with sorting/filtering
- Export to Excel/CSV

**Why Dashboard:**
- Frequently used
- Simple aggregation
- Benefits from visual charts
- Quick to build

#### 2. Top Owners by Name ✅ Dashboard
**Complexity:** Low
**Frequency:** High
**Visual Value:** High (bar charts)
**Python Script:** `top_owners_by_name.py`

**Dashboard Features:**
- Same as Top Owners by Address
- Additional: Show sample addresses for each owner

**Why Dashboard:**
- Frequently used
- Simple aggregation
- Benefits from visual charts

#### 3. LLC Analysis ✅ Dashboard
**Complexity:** Medium
**Frequency:** High
**Visual Value:** High (pie charts, bar charts)
**Python Script:** `llc_analysis.py`

**Dashboard Features:**
- Town selector
- Pie chart: LLC vs Non-LLC breakdown
- Bar chart: Top LLC owners
- Table: Detailed breakdown
- Export functionality

**Why Dashboard:**
- Frequently used
- Great visual representation (pie charts)
- Standard analysis pattern

#### 4. Property Type Breakdown ✅ Dashboard
**Complexity:** Low
**Frequency:** Medium
**Visual Value:** High (pie charts)
**SQL Query:** Available in TABLEPLUS_QUERIES.sql

**Dashboard Features:**
- Town selector
- Pie chart: Property types distribution
- Bar chart: Property types by count
- Table: Detailed breakdown with averages

**Why Dashboard:**
- Simple aggregation
- Great for visual exploration
- Quick to implement

#### 5. Ownership by Location ✅ Dashboard
**Complexity:** Low
**Frequency:** Medium
**Visual Value:** Medium (bar charts)
**New Analysis:** Not yet implemented

**Dashboard Features:**
- Town selector
- Group by: State or City
- Bar chart: Properties by owner location
- Table: Detailed breakdown

**Why Dashboard:**
- Simple aggregation
- Visual helps identify patterns
- Quick to implement

### Complex Analyses (Keep as Python Scripts)

These require complex logic, custom formatting, or multi-step processing:

#### 1. Custom Multi-Step Analysis ❌ Python Script
**Examples:**
- Combine multiple data sources
- Complex filtering logic
- Custom Excel formatting requirements
- Multi-sheet reports with specific layouts

**Why Python:**
- Full flexibility
- Complex logic easier in Python
- Perfect Excel formatting control

#### 2. Scheduled/Automated Reports ❌ Python Script
**Examples:**
- Weekly ownership reports
- Automated email reports
- Data quality checks

**Why Python:**
- Can be scheduled with cron
- Can automate email delivery
- Can integrate with other systems

#### 3. One-Time Deep Dives ❌ Python Script
**Examples:**
- Investigating specific data issues
- Custom analysis for specific project
- Experimental analysis

**Why Python:**
- Full flexibility
- No need to build UI for one-time use
- Can iterate quickly

#### 4. Complex Aggregations ❌ Python Script
**Examples:**
- Fuzzy matching owner names
- Complex grouping logic
- Multi-level aggregations
- Statistical analysis

**Why Python:**
- Python libraries (pandas, scipy) better for complex analysis
- Easier to debug
- More flexible

## Dashboard Feature Priority

### Phase 1: Core Analyses (High Priority)
1. **Top Owners by Mailing Address** - Most frequently used
2. **Top Owners by Name** - Frequently used
3. **LLC Analysis** - High visual value

**Effort:** 2-3 weeks
**Value:** High - covers 80% of common use cases

### Phase 2: Additional Visualizations (Medium Priority)
4. **Property Type Breakdown** - Good visual value
5. **Ownership by Location** - Useful insight

**Effort:** 1 week
**Value:** Medium - nice to have

### Phase 3: Advanced Features (Low Priority)
6. **Custom Query Builder** - Limited flexibility
7. **Saved Queries** - Convenience feature
8. **Comparison Views** - Compare multiple towns

**Effort:** 2-3 weeks
**Value:** Low - Python scripts handle complex cases

## Dashboard vs Python Script Decision Matrix

| Feature | Dashboard | Python Script |
|---------|-----------|---------------|
| **Standard Analysis** | ✅ | ⚠️ (if need custom formatting) |
| **Quick Insights** | ✅ | ❌ |
| **Visual Charts** | ✅ | ⚠️ (can add, but more work) |
| **Complex Logic** | ❌ | ✅ |
| **Custom Formatting** | ❌ | ✅ |
| **Multi-Step Analysis** | ❌ | ✅ |
| **Scheduled Reports** | ❌ | ✅ |
| **One-Time Analysis** | ❌ | ✅ |
| **Team Sharing** | ✅ | ⚠️ (share files) |
| **Non-Technical Users** | ✅ | ❌ |

## Implementation Strategy

### Dashboard Should Include:
- ✅ Pre-built analyses (top owners, LLC)
- ✅ Visual charts (bar, pie, line)
- ✅ Interactive exploration
- ✅ Export functionality
- ✅ Town/municipality filtering
- ✅ Top N limits

### Dashboard Should NOT Include:
- ❌ Full SQL query builder (use SQL interface instead)
- ❌ Complex multi-step analysis
- ❌ Custom Excel formatting
- ❌ Scheduled/automated reports
- ❌ One-time custom analyses

### Python Scripts Should Handle:
- ✅ Complex custom analyses
- ✅ Formatted reports
- ✅ Multi-step processing
- ✅ Scheduled/automated reports
- ✅ One-time deep dives
- ✅ Complex aggregations

## User Workflow

### For Standard Analyses:
1. User goes to Dashboard (`/analytics`)
2. Selects analysis type (Top Owners, LLC, etc.)
3. Selects town
4. Views charts and table
5. Exports if needed

### For Complex Analyses:
1. User identifies need for custom analysis
2. Uses Python script template
3. Customizes script as needed
4. Runs script
5. Gets formatted Excel output

### For Quick Queries:
1. User goes to SQL Query Interface (`/query`)
2. Writes SQL query
3. Views results
4. Exports if needed

## Conclusion

**Dashboard Focus:**
- Standard, frequently-used analyses
- Visual exploration
- Quick insights
- Non-technical users

**Python Scripts Focus:**
- Complex, custom analyses
- Formatted reports
- Scheduled/automated
- One-time deep dives

**SQL Interface Focus:**
- Quick ad-hoc queries
- Testing hypotheses
- Team collaboration

This separation ensures each tool is used for what it's best at.
