# Northwind Metals Corp - Shareholder Intelligence System

Take-home assignment: Shareholder intelligence platform for tracking ownership of a US public company.

## Overview

This system reconciles two critical data sources:
1. **Share Register**: Official list of registered holders (transfer agent system)
2. **SEC Filings**: SC 13D/G forms filed by holders with 5%+ ownership

The CFO reviews ownership changes weekly via an interactive Monday morning dashboard.

## Quick Start

```bash
# 1. Set up Python environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Clean and load data into database (MUST run all 3 in order)
python src/clean_data.py          # Step 1: Remove duplicates
python src/load_data.py           # Step 2: Create database
python src/create_holder_mapping.py  # Step 3: Create holder-filer mapping (REQUIRED)

# 4. Verify setup worked
sqlite3 northwind.db ".tables"    # Should show: beneficial_filings holders holder_filer_mapping opening_positions register_events shares_outstanding
sqlite3 northwind.db "SELECT COUNT(*) FROM holder_filer_mapping;"  # Should return: 5
sqlite3 northwind.db < queries/query1_top_holders.sql | head -5    # Should show top 3 holders

# 5. Run the Monday morning dashboard
streamlit run src/dashboard.py
# Expected: Browser opens to http://localhost:8501
# You should see:
#   - 0 ACTIVIST INTENT alerts (13G→13D conversions)
#   - 3 alerts for 10% Threshold Crossings
#   - 2 alerts for 5% Threshold Crossings
#   - Top holder: Ridgeline Capital Partners LP with 4,300,000 shares (10.54%)
```

**Important:** You MUST run all three data setup scripts before launching the dashboard. The `create_holder_mapping.py` script creates the `holder_filer_mapping` table which is required by the top holders query.

The dashboard will open in your browser at `http://localhost:8501`

## Project Structure

```
├── data/                          # Original raw CSV files
├── clean_data/                    # Cleaned CSV files (after duplicate removal)
├── src/
│   ├── schema.sql                 # Database table definitions
│   ├── clean_data.py              # Data cleaning script (removes duplicates)
│   ├── load_data.py               # Database loader (idempotent)
│   ├── create_holder_mapping.py  # Fuzzy matching between register and SEC systems
│   ├── dashboard.py               # Streamlit Monday morning dashboard ⭐
│   ├── queries/
│   │   └── dashboard_queries.py   # Query wrapper functions
│   └── utils/
│       ├── colors.py              # Color scheme constants
│       └── formatting.py          # Number/date formatters
├── queries/
│   ├── query1_top_holders.sql            # Top 10 shareholders reconciliation
│   ├── query2_weekly_activity.sql        # Weekly buy/sell by holder type
│   ├── query3_percent_reconciliation.sql # SEC filing % validation
│   ├── query4_watch_list.sql             # Threshold crossings + 13G→13D changes
│   ├── query5_sable_point_temporal.sql   # Late-recorded event impact analysis
│   ├── query6_shares_outstanding.sql     # Register integrity validation
│   ├── dashboard_top_movers.sql          # Top 5 weekly movers (for dashboard)
│   ├── query1_decisions.md               # Decision documentation for each query
│   ├── query2_decisions.md
│   └── ... (decision docs for all queries)
├── northwind.db                   # SQLite database (created by load_data.py)
├── DATA_FRESHNESS.md              # Engineering guide: keeping dashboard data correct
├── MONDAY_SCREEN_SUMMARY.md       # Dashboard documentation with alert rules
├── FAULT_LIST.md                  # Comprehensive data quality issue list (25 items)
├── PROMPT_LOG.md                  # Complete chronicle of Claude Code usage (20 prompts)
└── requirements.txt               # Python dependencies
```

## Data Pipeline

### Step 1: Data Cleaning
```bash
python src/clean_data.py
```

**What it does:**
- Removes duplicate event_id in register_events.csv (E1040)
- Removes duplicate accession_no in beneficial_filings.csv
- Copies other files unchanged to clean_data/

### Step 2: Database Loading
```bash
python src/load_data.py
```

**What it does:**
- Creates SQLite database (northwind.db)
- Loads cleaned CSV files into 5 core tables:
  - holders (versioned holder records)
  - opening_positions (starting balances as of May 31, 2026)
  - register_events (complete audit trail of share movements)
  - shares_outstanding (company-reported total shares)
  - beneficial_filings (SEC 13D/G filings)

**Idempotent:** Safe to run multiple times (drops and recreates tables)

### Step 3: Identity Mapping
```bash
python src/create_holder_mapping.py
```

**What it does:**
- Fuzzy string matching between register holder names and SEC filer names
- Creates holder_filer_mapping.csv in clean_data/
- Resolves identity across two systems (e.g., "Ridgeline Capital Partners LP" vs "L.P.")

## Six Core Queries

Run any query directly:
```bash
sqlite3 northwind.db < queries/query1_top_holders.sql
```

### Query 1: Top Holders
**Question:** Top 10 largest owners on August 31, 2026
**Key Logic:**
- Reconciles register holdings with SEC filings
- Uses MAX(register, SEC) logic to avoid double-counting
- Excludes CEDE & CO (nominee, not beneficial owner)

### Query 2: Last Week Activity
**Question:** Who bought/sold during August 24-28, 2026 by holder type?
**Key Logic:**
- Aggregates by holder type (institution, individual, insider)
- Uses holder type as of report date for ALL transactions
- Excludes NULL holders (corporate actions)

### Query 3: Percent Reconciliation
**Question:** Do SEC-reported percentages match our calculations?
**Key Logic:**
- Compares filer-reported % to our computed %
- Explains differences (stale outstanding_basis, indirect holdings)
- MAX logic for position calculation

### Query 4: Watch List
**Question:** Threshold crossings (5%, 10%) and 13G→13D conversions (June-August)
**Key Logic:**
- Uses LAG window function to detect crossings
- Pattern matching for form type changes (13G → 13D)
- Shows event_date vs filing_date (when it happened vs when we learned it)

### Query 5: Sable Point Temporal
**Question:** Position on July 31 "as we knew it then" vs "as we know it today"
**Key Logic:**
- Demonstrates temporal tracking (effective_date vs recorded_at)
- Shows impact of late-recorded reversals
- Critical for understanding data quality

### Query 6: Shares Outstanding Reconciliation
**Question:** Does register total match company-reported shares outstanding?
**Key Logic:**
- Register Total = Opening + Equity Issued - Buybacks
- Detects corporate actions via NULL holder patterns
- Validates register integrity (both dates show 0 variance)

## Monday Morning Dashboard

### Running the Dashboard
```bash
streamlit run src/dashboard.py
```

### Dashboard Sections (in priority order)

**1. Watch List Alerts (FIRST - Priority 1)**
- Red badges for 13G→13D conversions (activist intent)
- Orange/yellow badges for threshold crossings (5%, 10%)
- Full alert table with filing lag indicators
- Download CSV of all alerts June-August

**2. Weekly Activity Pulse (SECOND - Priority 2)**
- Summary by holder type (institutions, individuals, insiders)
- Top 5 most active individual holders
- Green highlighting for net buyers, red for net sellers
- Download CSV of transaction-level activity

**3. Top 10 Shareholders (THIRD - Priority 3)**
- Reconciled positions (register + SEC)
- Percentage of company owned
- Reconciliation status indicators
- Data quality validation panel

**4. System Limitations (Collapsible Footer)**
- Plain language explanation of what we can/cannot see
- Reconciliation methodology
- Data freshness indicators

### Three Alert Rules (CFO Documentation)

**ALERT #1: ACTIVIST INTENT DETECTED** 🚨
- **Trigger:** Investor converted from passive (13G) to activist (13D) filing
- **CFO Action:** Contact IR, brief board, review defenses, prepare response strategy

**ALERT #2: MAJOR THRESHOLD CROSSING** ⚠️
- **Trigger:** Ownership crossed 5% or 10% threshold (up or down)
- **CFO Action:** Monitor accumulation patterns, assess investor profile, prepare engagement

**ALERT #3: LATE FILING DISCLOSURE** ℹ️
- **Trigger:** SEC filing received >3 days after transaction date
- **CFO Action:** Document delay, assess credibility implications

## Data Architecture

### Temporal Tracking
This system tracks both **when events happened** and **when we learned about them**:
- `effective_date` / `event_date` = when the transaction occurred (legal reality)
- `recorded_at` / `filing_date` = when we received the information (knowledge reality)

This dual-timestamp pattern enables:
- "As of" queries showing what was known at a historical date
- Detecting late-filed reversals that change past positions
- Reconciliation between register and SEC filing timelines

### Key Reconciliation Patterns

**MAX Logic (not SUM):**
```
Best Estimate = MAX(register_shares, sec_shares)
```
Why? SEC filing already includes direct register holdings. Summing would double-count.

**Reversal Exclusion:**
```sql
WHERE transfer_id NOT IN (
  SELECT reverses_transfer_id
  FROM register_events
  WHERE reverses_transfer_id IS NOT NULL
)
```

**Holder Version Resolution:**
```sql
WHERE version = (
  SELECT MAX(version)
  FROM holders
  WHERE holder_id = ? AND valid_from <= target_date
)
```

## Data Freshness & Integrity

**See [DATA_FRESHNESS.md](DATA_FRESHNESS.md)** for complete engineering guide on maintaining dashboard accuracy.

**Key Topics Covered:**
- **Data pipeline:** How register changes reach the dashboard (recommended architecture with latencies)
- **Late reversals:** How backdated corrections affect historical views
- **"As of" semantics:** What dashboard dates mean (effective_date vs recorded_at)
- **Staleness detection:** Monitoring, validation checks, and failure modes

**Quick Reference:**
- Dashboard uses `effective_date` filtering (legal reality, not knowledge cutoff)
- Late-recorded reversals retroactively correct historical positions
- Recommended refresh: 5-15 min (register) + 5 min (cache) = ~20 min latency
- Validation: Query 6 reconciliation must show 0 variance

## Known Data Quality Issues

**See [FAULT_LIST.md](FAULT_LIST.md)** for comprehensive documentation of all 25 data quality issues found.

**Summary:**
- **2 Data errors (FIXED):** Duplicate event_id E1040 and duplicate accession_no 0002233445-26-000077 - removed by `src/clean_data.py`
- **12 Expected features:** Name variations, holder changes, temporal lags, partial reversals, filing inconsistencies - handled by schema design and fuzzy matching
- **11 Validation checks (PASSED):** Referential integrity, temporal ordering, share positivity, percentage calculations

The synthetic data intentionally contains realistic faults to simulate production systems. All data errors have been resolved; expected features are handled through appropriate schema design, fuzzy matching, and query logic.

## Dependencies

- **Python 3.9 or higher** (tested on 3.9, 3.10, 3.11)
- pandas 2.0+ (data processing)
- streamlit 1.28+ (dashboard)
- thefuzz 0.20+ (fuzzy string matching)
- reportlab 4.0+ (optional PDF generation)

SQLite is built into Python (no separate install needed).

**Note:** If you get type hint errors on Python 3.9, the code has been updated to use `Union` types for compatibility.

## Contact

For questions about this system:
- shareholderservices@northwind.example.com

---
**Assignment completed by:** [Your Name]
**Date:** [Date]
**Time spent:** [Hours]
