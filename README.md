# Northwind Metals Corp - Shareholder Intelligence System

Take-home assignment: Shareholder intelligence platform for tracking ownership of a US public company.

## Overview

This system reconciles two critical data sources:
1. **Share Register**: Official list of registered holders (transfer agent system)
2. **SEC Filings**: SC 13D/G forms filed by holders with 5%+ ownership

The CFO reviews ownership changes weekly via an interactive Monday morning dashboard.

**📋 Assignment Documentation:** All deliverable explanations and documentation are in the `documents/` folder (see [Assignment Documentation](#assignment-documentation) section below).

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

## Project Structure (GitHub)

```
├── ASSIGNMENT.md                  # Original assignment instructions
├── README.md                      # This file
├── requirements.txt               # Python dependencies
├── data/                          # Original raw CSV files (5 CSVs)
│   ├── beneficial_filings.csv
│   ├── holders.csv
│   ├── opening_positions.csv
│   ├── register_events.csv
│   └── shares_outstanding.csv
├── clean_data/                    # Cleaned CSV files (created by clean_data.py)
│   ├── beneficial_filings.csv
│   ├── holder_filer_mapping.csv
│   ├── holders.csv
│   ├── opening_positions.csv
│   ├── register_events.csv
│   └── shares_outstanding.csv
├── documents/                     # Assignment documentation
│   ├── six_questions_explanations.txt
│   ├── document_CFO.txt
│   ├── document_for_engineer.txt
│   ├── fault_details.txt
│   └── PROMPT_LOG.md
├── queries/                       # SQL queries for 6 assignment questions + dashboard
│   ├── query1_top_holders.sql
│   ├── query2_weekly_activity.sql
│   ├── query3_percent_reconciliation.sql
│   ├── query4_watch_list.sql
│   ├── query5_sable_point_temporal.sql
│   ├── query6_shares_outstanding.sql
│   └── dashboard_top_movers.sql
└── src/                           # Python implementation
    ├── schema.sql
    ├── clean_data.py
    ├── load_data.py
    ├── create_holder_mapping.py
    ├── dashboard.py
    ├── pdf/
    │   ├── __init__.py
    │   └── generator.py
    ├── queries/
    │   ├── __init__.py
    │   └── dashboard_queries.py
    └── utils/
        ├── __init__.py
        ├── colors.py
        └── formatting.py

Note: northwind.db (SQLite database) is created locally by load_data.py and excluded from git.
```

## Assignment Documentation

All assignment deliverables are in the `documents/` folder:

- **`six_questions_explanations.txt`** - Detailed explanations for all 6 SQL queries with key decisions and business logic
- **`document_CFO.txt`** - Half-page summary of 3 alert rules in business language for CFO
- **`document_for_engineer.txt`** - One-page technical guide on data freshness and pipeline architecture
- **`fault_details.txt`** - Complete list of 25 data quality issues (2 fixed, 12 expected, 11 validated)
- **`PROMPT_LOG.md`** - Complete chronicle of Claude Code usage with collaboration patterns

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

All queries can be run directly with column headers:

```bash
# Query 1: Top 10 largest owners on August 31, 2026
sqlite3 -header -column northwind.db < queries/query1_top_holders.sql

# Query 2: Weekly buy/sell activity by holder type (Aug 24-28)
sqlite3 -header -column northwind.db < queries/query2_weekly_activity.sql

# Query 3: SEC-reported % vs calculated % reconciliation
sqlite3 -header -column northwind.db < queries/query3_percent_reconciliation.sql

# Query 4: Watch list (threshold crossings + 13G→13D changes, June-Aug)
sqlite3 -header -column northwind.db < queries/query4_watch_list.sql

# Query 5: Sable Point temporal comparison (July 31 then vs now)
sqlite3 -header -column northwind.db < queries/query5_sable_point_temporal.sql

# Query 6: Register total vs company-reported shares outstanding
sqlite3 -header -column northwind.db < queries/query6_shares_outstanding.sql
```

**Detailed explanations:** See `documents/six_questions_explanations.txt` for key decisions, business logic, and technical approach for all 6 queries.

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

### Alert Rules

See `documents/document_CFO.txt` for detailed alert rules documentation (3 alerts: Activist Intent, Threshold Crossing, Late Filing).

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

See `documents/document_for_engineer.txt` for engineering guide on data pipeline, late reversals, "as of" semantics, and staleness detection.

## Known Data Quality Issues

See `documents/fault_details.txt` for complete list of 25 data quality issues (2 fixed, 12 expected, 11 validated).

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
