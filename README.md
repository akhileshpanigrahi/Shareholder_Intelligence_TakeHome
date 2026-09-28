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
#   - 1 ACTIVIST INTENT alert (13G→13D conversion)
#   - 1 alert for 10% Threshold Crossing
#   - 5 alerts for 5% Threshold Crossings
#   - Top holder: Ridgeline Capital Partners LP with 4,300,000 shares (10.54%)
```

**Important:** You MUST run all three data setup scripts before launching the dashboard. The `create_holder_mapping.py` script creates the `holder_filer_mapping` table which is required by the top holders query.

The dashboard will open in your browser at `http://localhost:8501`

## Project Structure

```
├── data/                          # Original raw CSV files (5 CSVs)
├── clean_data/                    # Cleaned CSV files (6 files: 5 CSVs + holder_filer_mapping)
├── EDA/                           # Exploratory data analysis notebooks
├── src/
│   ├── schema.sql                 # Database table definitions
│   ├── clean_data.py              # Data cleaning script (removes duplicates)
│   ├── load_data.py               # Database loader (idempotent)
│   ├── create_holder_mapping.py  # Fuzzy matching between register and SEC systems
│   ├── dashboard.py               # Streamlit Monday morning dashboard ⭐
│   ├── pdf/
│   │   ├── generator.py           # PDF executive summary generator
│   │   └── __init__.py
│   ├── queries/
│   │   ├── dashboard_queries.py   # Query wrapper functions
│   │   └── __init__.py
│   └── utils/
│       ├── colors.py              # Color scheme constants
│       ├── formatting.py          # Number/date formatters
│       └── __init__.py
├── queries/
│   ├── query1_top_holders.sql            # Top 10 shareholders reconciliation
│   ├── query1_decisions.md               # Decision documentation for query 1
│   ├── query2_weekly_activity.sql        # Weekly buy/sell by holder type
│   ├── query2_decisions.md
│   ├── query3_percent_reconciliation.sql # SEC filing % validation
│   ├── query3_decisions.md
│   ├── query4_watch_list.sql             # Threshold crossings + 13G→13D changes
│   ├── query4_decisions.md
│   ├── query5_sable_point_temporal.sql   # Late-recorded event impact analysis
│   ├── query5_decisions.md
│   ├── query6_shares_outstanding.sql     # Register integrity validation
│   ├── query6_decisions.md
│   └── dashboard_top_movers.sql          # Top 5 weekly movers (for dashboard)
├── northwind.db                   # SQLite database (created by load_data.py)
├── ASSIGNMENT.md                  # Original assignment instructions
├── CLAUDE.md                      # Project guidance for Claude Code
├── DATA_FRESHNESS.md              # Engineering guide: keeping dashboard data correct
├── MONDAY_SCREEN_SUMMARY.md       # Dashboard documentation with alert rules
├── FAULT_LIST.md                  # Comprehensive data quality issue list (25 items)
├── PROMPT_LOG.md                  # Complete chronicle of Claude Code usage (20 prompts)
├── DELIVERABLES_REVIEW.md         # Final deliverables review report
├── QUERY_REVIEW.md                # Query verification and validation report
├── requirements.txt               # Python dependencies
└── __init__.py                    # Package initialization
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

All queries can be run directly with column headers displayed:

### Query 1: Top Holders
**Question:** Top 10 largest owners on August 31, 2026

**Run with:**
```bash
sqlite3 -header -column northwind.db < queries/query1_top_holders.sql
```

**Key Logic:**
- Reconciles register holdings with SEC filings
- Uses MAX(register, SEC) logic to avoid double-counting
- Excludes CEDE & CO (nominee, not beneficial owner)

---

### Query 2: Last Week Activity
**Question:** Who bought/sold during August 24-28, 2026 by holder type?

**Run with:**
```bash
sqlite3 -header -column northwind.db < queries/query2_weekly_activity.sql
```

**Key Logic:**
- Aggregates by holder type (institution, individual, insider)
- Uses holder type as of report date for ALL transactions
- Excludes NULL holders (corporate actions)

---

### Query 3: Percent Reconciliation
**Question:** Do SEC-reported percentages match our calculations?

**Run with:**
```bash
sqlite3 -header -column northwind.db < queries/query3_percent_reconciliation.sql
```

**Key Logic:**
- Compares filer-reported % to our computed %
- Explains differences (stale outstanding_basis, indirect holdings)
- MAX logic for position calculation

---

### Query 4: Watch List
**Question:** Threshold crossings (5%, 10%) and 13G→13D conversions (June-August)

**Run with:**
```bash
sqlite3 -header -column northwind.db < queries/query4_watch_list.sql
```

**Key Logic:**
- Uses LAG window function to detect crossings
- Pattern matching for form type changes (13G → 13D)
- Shows event_date vs filing_date (when it happened vs when we learned it)

---

### Query 5: Sable Point Temporal
**Question:** Position on July 31 "as we knew it then" vs "as we know it today"

**Run with:**
```bash
sqlite3 -header -column northwind.db < queries/query5_sable_point_temporal.sql
```

**Key Logic:**
- Demonstrates temporal tracking (effective_date vs recorded_at)
- Shows impact of late-recorded reversals
- Critical for understanding data quality

---

### Query 6: Shares Outstanding Reconciliation
**Question:** Does register total match company-reported shares outstanding?

**Run with:**
```bash
sqlite3 -header -column northwind.db < queries/query6_shares_outstanding.sql
```

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

**Engineering Guide Topics:**
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

**Summary of 25 documented data quality issues:**
- **2 Data errors (FIXED):** Duplicate event_id E1040 and duplicate accession_no 0002233445-26-000077 - removed by `src/clean_data.py`
- **12 Expected features:** Name variations, holder changes, temporal lags, partial reversals, filing inconsistencies - handled by schema design and fuzzy matching
- **11 Validation checks (PASSED):** Referential integrity, temporal ordering, share positivity, percentage calculations

The synthetic data intentionally contains realistic faults to simulate production systems. All data errors have been resolved; expected features are handled through appropriate schema design, fuzzy matching, and query logic.

## Dependencies

- **Python 3.9 or higher** (tested on 3.9, 3.10, 3.11)
- pandas 2.0+ (data processing)
- numpy 1.24+ (numerical operations)
- streamlit 1.28+ (dashboard)
- thefuzz 0.20+ (fuzzy string matching)
- python-Levenshtein 0.20+ (string similarity - improves thefuzz performance)
- reportlab 4.0+ (PDF generation for executive summaries)

SQLite is built into Python (no separate install needed).

**Note:** If you get type hint errors on Python 3.9, the code has been updated to use `Union` types for compatibility.

---

**Assignment completed by:** [Your Name]
**Date:** [Date]
**Time spent:** [Hours]
