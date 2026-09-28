# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a shareholder intelligence system for tracking ownership of Northwind Metals Corp, a US public company. The system reconciles two data sources:
1. **Share Register**: Official list of registered holders (mostly CEDE & CO nominee)
2. **SEC Filings**: SC 13D/G forms filed by holders with 5%+ ownership

The CFO reviews ownership changes weekly, focusing on who bought/sold, threshold crossings (5%, 10%), and form type changes (13G to 13D indicating activist intent).

## Data Architecture

### Core Concept: Temporal Tracking
This system tracks both **when events happened** and **when we learned about them**:
- `effective_date` / `event_date` = when the transaction occurred (legal reality)
- `recorded_at` / `filing_date` = when we received the information (knowledge reality)

This dual-timestamp pattern is critical for:
- "As of" queries showing what was known at a specific historical date
- Detecting late-filed reversals that change past positions
- Reconciliation between register and SEC filing timelines

### Data Sources (clean_data/ folder)

- **holders.csv**: Versioned holder records tracking name/type changes via `valid_from` dates
- **opening_positions.csv**: Starting balances as of 2026-05-31
- **register_events.csv**: Complete audit trail of share movements between holders
  - Contains reversals via `reverses_transfer_id` field
  - `effective_date` vs `recorded_at` distinguish transaction time from recording time
- **shares_outstanding.csv**: Company-reported total shares by date
- **beneficial_filings.csv**: SEC 13D/G filings with ownership percentages
  - Amendments link via `amends_accession_no`
  - Contains `outstanding_basis` showing what denominator filers used
- **holder_filer_mapping.csv**: Generated mapping between holder_id and filer_cik
  - Created via fuzzy string matching in `src/create_holder_mapping.py`
  - Resolves identity across register and SEC systems
  - Can be manually edited and reloaded if needed

### Known Data Quality Issues

The synthetic data intentionally contains real-world faults:
- **Duplicate records** (cleaned by src/clean_data.py):
  - register_events.csv: Duplicate event_id E1040
  - beneficial_filings.csv: Duplicate accession_no 0002233445-26-000077
- Late-recorded reversals (recorded_at after effective_date)
- Name variations across systems (e.g., "Ridgeline Capital Partners LP" vs "L.P.")
- Holder type changes (individual → insider)
- Inconsistent shares_outstanding bases in SEC filings
- Duplicate transactions requiring reversal

## Database Commands

### Setup and Loading

```bash
# Activate virtual environment
source .venv/bin/activate

# Step 1: Clean raw data (removes duplicates, fixes data quality issues)
# Reads from data/ and writes to clean_data/
python src/clean_data.py

# Step 2: Load cleaned data into SQLite (idempotent - creates schema and loads all CSVs)
# Reads from clean_data/
python src/load_data.py

# Step 3: Create holder-filer mapping (fuzzy matching between register and SEC)
python src/create_holder_mapping.py

# Verify database structure
sqlite3 northwind.db ".tables"
```

### Query Execution

```bash
# Run SQL queries
sqlite3 northwind.db < queries/query_name.sql

# Interactive mode
sqlite3 northwind.db
```

## Key Implementation Challenges

### 1. Holder Identity Resolution
Reconcile the same entity across:
- Name variations (with/without punctuation, legal suffixes)
- System boundaries (register holder_id vs SEC filer_cik)
- Temporal changes (name changes, holder type reclassifications)

### 2. Point-in-Time Position Calculation
Compute holdings "as we knew it on date X" requires:
- Opening position (2026-05-31)
- Register events WHERE recorded_at <= X
- Exclude reversed transfers even if reversal recorded after date X
- Apply holder versions valid on that date

### 3. Reconciliation Logic
Top holders must merge:
- Register positions (direct holdings on share register)
- SEC reported positions (total beneficial ownership including direct)
- **Best estimate = MAX(register, SEC)** not SUM
  - SEC filing already includes direct register holdings
  - Summing would double-count shares
  - Example: Ridgeline has 2.9M direct + 4.3M SEC total = 4.3M, not 7.2M

Handle percentage calculations:
- Compute from actual shares outstanding on the date
- Compare to filer's reported percent (often based on stale outstanding_basis)
- Document all differences

**CEDE & CO Treatment**:
- CEDE (H001) is a nominee holding ~33M shares
- Exclude from top holders list (not a beneficial owner)
- Holders in holders.csv are SEPARATE from CEDE
- Only SEC filers without holder_id mapping are inside CEDE

### 4. Threshold Crossing Detection
Monitor 5% and 10% thresholds:
- Calculate position as % of shares_outstanding on each date
- Detect crossings in both directions (up and down)
- Report event_date (when it happened) vs filing_date (when we learned it)

### 5. Form Type Change Monitoring
Track 13G → 13D conversions (passive to activist):
- Compare form_type in amendment chains via amends_accession_no
- This is a key CFO alert (activist investors)

## Development Notes

### SQLite Limitations and Workarounds
- **No FULL OUTER JOIN**: Use UNION of all keys + LEFT JOIN pattern
  ```sql
  all_holders AS (
    SELECT holder_id FROM register_view
    UNION
    SELECT holder_id FROM sec_view
  )
  SELECT * FROM all_holders
  LEFT JOIN register_view USING (holder_id)
  LEFT JOIN sec_view USING (holder_id)
  ```
- **No GREATEST() function**: Use nested CASE statements
  ```sql
  CASE WHEN a > b THEN a ELSE b END
  ```
- **No recursive CTEs**: Amendment chain resolution requires NOT EXISTS pattern instead

### SQL Schema Patterns
- All tables use TEXT for dates (YYYY-MM-DD format) for SQLite compatibility
- Composite primary keys enforce data integrity (e.g., holder_id + version)
- NULLable foreign keys handle edge cases (equity issuance, share buybacks)
- Reversal pattern uses self-referential foreign key (reverses_transfer_id)

### Position Calculation Pattern
```sql
-- Starting point
SELECT shares FROM opening_positions WHERE holder_id = ? AND as_of_date = '2026-05-31'

-- Plus movements
+ SUM(shares WHERE to_holder_id = ? AND effective_date <= target_date)
- SUM(shares WHERE from_holder_id = ? AND effective_date <= target_date)

-- Excluding reversals
AND transfer_id NOT IN (SELECT reverses_transfer_id FROM register_events WHERE reverses_transfer_id IS NOT NULL)
```

### Amendment Chain Resolution
```sql
-- Get latest filing (NOT amended by any other filing)
SELECT bf1.*
FROM beneficial_filings bf1
WHERE bf1.filing_date <= '2026-08-31'
  AND NOT EXISTS (
    SELECT 1 FROM beneficial_filings bf2
    WHERE bf2.amends_accession_no = bf1.accession_no
      AND bf2.filing_date <= '2026-08-31'
  )
```

### Query Structure Pattern
Each query should have:
1. **The SQL file**: `queries/queryN_name.sql` - runnable via `sqlite3 northwind.db < queries/queryN_name.sql`
2. **Decision documentation**: `queries/queryN_decisions.md` - explains all choices made for the assignment requirement "say what you decided and why"

The decision doc should cover:
- Date filter choices (system view vs actual position)
- How reversals are handled
- Identity reconciliation approach
- Any assumptions about data or run date
- Edge cases and how they're treated

### Key Learnings from Completed Queries

**Query 1 - Top Holders:**
- **System View vs Actual Position:**
  - For "what the CFO knew on Aug 31", use `recorded_at` (register) and `filing_date` (SEC)
  - For "actual position on Aug 31", use `effective_date` (register) and `event_date` (SEC)
  - Late-recorded reversals affect system view differently than actual position
- **Holder Version Resolution:**
  - Use latest holder version: `WHERE version = (SELECT MAX(version) FROM holders WHERE holder_id = ?)`
  - Critical for fuzzy matching (name changes like "Holdings LLC" → "Office LLC")
- **Unmapped SEC Filers:**
  - Some SEC filers have no holder_id (e.g., Vantage Quant Strategies)
  - These are beneficial owners behind CEDE with no direct register presence
  - Include them with register_shares = 0, sec_shares from filing

**Query 2 - Weekly Activity:**
- **Option A Consolidation Pattern:**
  - When holder_type changes during the period, use the type as of report date for ALL transactions
  - Rationale: CFO wants to know "which current holder types were active"
  - Example: If H005 changed from "individual" to "insider" on Aug 26, ALL Aug 24-28 transactions count under "insider"
- **NULL Holder Handling:**
  - `to_holder_id IS NULL` = share buyback (exclude from shareholder activity)
  - `from_holder_id IS NULL` = equity issuance (exclude from shareholder activity)
  - Focus on shareholder-to-shareholder movements only
- **SQLite UNION Pattern for Aggregation:**
  - Cannot use FULL OUTER JOIN, use UNION of buyer and seller types
  - Then LEFT JOIN to combine buys and sells by type

**Query 3 - Percent Reconciliation:**
- **MAX Logic for Position Calculation:**
  - `our_shares = MAX(register_shares, shares_reported)` NOT register + SEC
  - SEC filing already includes direct register holdings, summing would double-count
  - If register > SEC = ERROR (impossible scenario requiring investigation)
  - If SEC > register = NORMAL (indirect holdings via CEDE & CO)
  - If register = SEC = PERFECT (all holdings are direct)
- **Historical Outstanding Shares:**
  - For event_dates before first shares_outstanding record, carry earliest available value backwards
  - Use COALESCE with fallback to handle missing historical data
  - Document assumption in decision file
- **Simplified Explanations:**
  - Focus on Match vs Mismatch with clear reasons
  - "Match: Indirect holdings via CEDE" is NORMAL and GOOD (most common case)
  - Only "Mismatch: Register exceeds SEC" requires immediate CFO attention
  - 0.01% tolerance for rounding differences

**Query 4 - Watch List:**
- **Chronological Comparison Pattern:**
  - Use `LAG()` window function partitioned by filer_cik, ordered by event_date, filing_date
  - Compare each filing to the previous filing chronologically (not amendment chains)
  - Rationale: Detects actual position changes over time
- **First Filing Treatment:**
  - Treat first filings as crossing from 0% if they're ≥5% or ≥10%
  - Example: New filer at 8% triggers both "Crossed above 5%" and "Crossed above 10%"
- **Multiple Threshold Alerts:**
  - Show all thresholds crossed in a single position change
  - If 4% to 11%, show two separate rows: "Crossed above 5%" and "Crossed above 10%"
  - Use separate CTEs for each alert type, combine with UNION ALL
- **Form Type Pattern Matching:**
  - Use `LIKE '%13G%'` and `LIKE '%13D%'` (NOT `'13G%'` / `'13D%'`)
  - Form types in database are "SC 13G", "SC 13D" with "SC " prefix
  - Critical for detecting passive-to-activist conversions (highest priority CFO alert)

**Query 5 - Sable Point Temporal Comparison:**
- **Event Type-Based Reversal Filtering:**
  - **Critical**: Changed from exclusion pattern to event_type filtering for partial reversals
  - "Then" view: `AND re.event_type != 'reversal'` (exclude reversal events we didn't know about yet)
  - "Now" view: Include ALL events (transfers and reversals), let natural netting occur
  - Rationale: Exclusion pattern loses unreverted portion of partial reversals
- **Partial Reversal Handling:**
  - Example: Original transfer +1,650,000, partial reversal -400,000
  - Exclusion pattern would exclude entire +1,650,000, losing the +1,250,000 unreverted portion
  - Event type + natural netting: +1,650,000 - 400,000 = +1,250,000 (correct!)
- **"Today" Definition:**
  - Assume "today" = September 1, 2026 for queries requiring current knowledge
  - Use `recorded_at <= '2026-09-01 23:59:59'` as current knowledge cutoff
  - Rationale: All register events and reversals through Aug 31 are recorded by Sept 1
- **Temporal Perspective Comparison:**
  - Same effective date (July 31), two knowledge dates (July 31 vs Sept 1)
  - Shows how late-recorded events change historical positions retroactively
  - Key CFO insight: Decisions made on historical data may be based on incomplete information

**Query 6 - Shares Outstanding Reconciliation:**
- **NULL Holder Pattern for Corporate Actions:**
  - `from_holder_id IS NULL` = Equity issuance (new shares created)
  - `to_holder_id IS NULL` = Share buyback/retirement (shares destroyed)
  - These transactions change total shares outstanding
  - All other transactions are shareholder-to-shareholder (no net change to outstanding)
- **Reconciliation Formula:**
  - Register Total = Opening Total + Equity Issued - Shares Repurchased
  - Compare to company-reported shares_outstanding from SEC filings
  - Perfect match validates register integrity
- **Date Selection:**
  - Use available shares_outstanding data points (June 30, Aug 3)
  - For "August 31" check, use closest available (Aug 3)
  - Assumes no changes between Aug 3-31 if no register movements
- **Key Validation:**
  - Both dates showed zero difference (perfect reconciliation)
  - Confirms register is complete and accurate
  - No missing shares or unrecorded movements
  - Opening positions (May 31) baseline is correct

## Deliverables Structure

1. **Schema + Loader**: SQL tables and idempotent data loading script
2. **Six Queries**: Top holders, weekly activity, percentage reconciliation, watch list, temporal comparison, shares outstanding validation
3. **Monday Screen**: Interactive dashboard for CFO (Streamlit/HTML/notebook)
4. **Data Freshness Doc**: One-page engineer guide on keeping data current
5. **Fault List**: Documented data quality issues and handling approach

## Code Organization

- `src/schema.sql`: Table definitions with comprehensive comments
- `src/clean_data.py`: Data cleaning script that removes duplicates and fixes data quality issues
- `src/load_data.py`: Idempotent loader for all 5 core CSV files (reads from clean_data/)
- `src/create_holder_mapping.py`: Fuzzy matching to create holder_filer_mapping table
- `src/dashboard.py`: Streamlit Monday morning dashboard (600+ lines)
- `src/queries/dashboard_queries.py`: Query wrapper class for dashboard data loading
- `src/utils/formatting.py`: Number/date formatters (Python 3.9+ compatible)
- `src/utils/colors.py`: Color scheme constants for dashboard
- `src/pdf/generator.py`: ReportLab PDF generator for executive summaries
- `queries/`: SQL queries and decision documentation for 6 assignment questions
- `queries/dashboard_top_movers.sql`: Dashboard-specific query for top 5 weekly movers
- `EDA/`: Exploratory analysis notebooks
- `data/`: Original raw CSV files (read-only)
- `clean_data/`: Cleaned CSV files created by clean_data.py and used by load_data.py
- `northwind.db`: SQLite database created by load_data.py
- `MONDAY_SCREEN_SUMMARY.md`: Complete dashboard documentation with alert rules
- `DATA_FRESHNESS.md`: Engineering guide for maintaining dashboard data accuracy
- `FAULT_LIST.md`: Comprehensive list of all data quality issues found (25 items: 2 fixed, 12 expected, 11 validated)
- `PROMPT_LOG.md`: Complete chronicle of Claude Code prompts and work completed (5 sessions, 20 major prompts)

## Dashboard Architecture

### Running the Dashboard

```bash
# Launch Monday morning dashboard
streamlit run src/dashboard.py
```

Dashboard opens at `http://localhost:8501`

### Dashboard Sections (Priority Order)

**1. Watch List Alerts (FIRST - Priority 1)**
- Critical governance alerts requiring immediate board attention
- Color-coded badges: RED (13G→13D), ORANGE (10%), YELLOW (5%)
- Full alert table with filing lag indicators
- Download: Watch list CSV (June 1 - August 31, 2026)

**2. Weekly Activity Pulse (SECOND - Priority 2)**
- Summary by holder type (institutions, individuals, insiders)
- Top 5 most active individual holders
- GREEN highlighting for net buyers, RED for net sellers
- Download: Weekly activity CSV (transaction-level detail)

**3. Top 10 Shareholders (THIRD - Priority 3)**
- Reconciled positions (register + SEC using MAX logic)
- Percentage of company owned
- Reconciliation status indicators
- Data quality validation panel

**4. System Limitations (Collapsible Footer)**
- Plain language explanation of what we can/cannot see
- Reconciliation methodology (MAX not SUM)
- Data freshness indicators

### Dashboard Data Loading Pattern

The dashboard uses a two-level caching strategy:

```python
@st.cache_resource
def get_query_executor():
    """Database connection (persistent across reruns)."""
    return DashboardQueries()

@st.cache_data(ttl=300)  # 5-minute cache
def load_dashboard_data():
    """Load all dashboard data from database."""
    queries = get_query_executor()
    return {
        'alert_summary': queries.get_alert_summary(),
        'watch_list': queries.get_watch_list(),
        'weekly_activity': queries.get_weekly_activity(),
        'top_movers': queries.get_top_movers(),
        'top_holders': queries.get_top_holders(),
        'shares_outstanding': queries.get_shares_outstanding_validation()
    }
```

### Color Scheme (src/utils/colors.py)

```python
# Alert severity colors
CRITICAL_RED = "#D32F2F"      # 13G→13D conversions
WARNING_ORANGE = "#F57C00"    # 10% threshold crossings
WARNING_YELLOW = "#FFA000"    # 5% threshold crossings

# Position change colors
BUYER_GREEN = "#388E3C"       # Net buyers
SELLER_RED = "#E53935"        # Net sellers
```

### Pandas Styling Pattern

When styling Streamlit dataframes, ensure the styling function returns the correct number of style values:

```python
def style_watch_row(row):
    """Style row based on alert type (returns N color values for N columns)."""
    alert_type = row['Alert Type']
    if '13D' in alert_type:
        bg_color = CRITICAL_RED
        text_color = 'white'
    elif '10%' in alert_type:
        bg_color = WARNING_ORANGE
        text_color = 'white'
    elif '5%' in alert_type:
        bg_color = WARNING_YELLOW
        text_color = 'black'
    else:
        return [''] * len(row)

    return [f'background-color: {bg_color}; color: {text_color}; font-weight: bold'] * len(row)

styled_df = display_df.style.apply(style_watch_row, axis=1)
st.dataframe(styled_df, width="stretch")
```

### Python 3.9 Compatibility

Use `Union` type hints instead of `|` operator (PEP 604 is Python 3.10+):

```python
from typing import Union, Optional

# Correct for Python 3.9+
def format_shares(shares: Union[int, float, None]) -> str:
    if shares is None:
        return "—"
    return f"{int(shares):,}"

# WRONG - requires Python 3.10+
def format_shares(shares: int | float | None) -> str:
    ...
```

## Implementation Status

**Completed:**
- ✅ Database schema (src/schema.sql)
- ✅ Data loader (src/load_data.py)
- ✅ Holder-filer identity mapping (src/create_holder_mapping.py)
- ✅ Query 1: Top holders with reconciliation (queries/query1_top_holders.sql + query1_decisions.md)
- ✅ Query 2: Weekly buy/sell activity by holder type (queries/query2_weekly_activity.sql + query2_decisions.md)
- ✅ Query 3: Percent ownership reconciliation (queries/query3_percent_reconciliation.sql + query3_decisions.md)
- ✅ Query 4: Watch list (threshold crossings + 13G→13D changes) (queries/query4_watch_list.sql + query4_decisions.md)
- ✅ Query 5: Sable Point temporal comparison (queries/query5_sable_point_temporal.sql + query5_decisions.md)
- ✅ Query 6: Shares outstanding reconciliation (queries/query6_shares_outstanding.sql + query6_decisions.md)
- ✅ Monday screen dashboard (src/dashboard.py + MONDAY_SCREEN_SUMMARY.md)
- ✅ PDF executive summary generator (src/pdf/generator.py)
- ✅ Data freshness documentation (DATA_FRESHNESS.md)

- ✅ Fault list compilation (FAULT_LIST.md)

**All deliverables complete.**
