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

### Data Sources (data/ folder)

- **holders.csv**: Versioned holder records tracking name/type changes via `valid_from` dates
- **opening_positions.csv**: Starting balances as of 2026-05-31
- **register_events.csv**: Complete audit trail of share movements between holders
  - Contains reversals via `reverses_transfer_id` field
  - `effective_date` vs `recorded_at` distinguish transaction time from recording time
- **shares_outstanding.csv**: Company-reported total shares by date
- **beneficial_filings.csv**: SEC 13D/G filings with ownership percentages
  - Amendments link via `amends_accession_no`
  - Contains `outstanding_basis` showing what denominator filers used

### Known Data Quality Issues

The synthetic data intentionally contains real-world faults:
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

# Create schema (idempotent)
sqlite3 northwind.db < src/schema.sql

# Load data (must be idempotent - runnable twice with same result)
# Note: Loader script not yet implemented
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
- Register positions (share register source of truth)
- SEC reported positions (beneficial ownership window into nominee)
- Best estimate = register + (SEC - any register position for that filer)

Handle percentage calculations:
- Compute from actual shares outstanding on the date
- Compare to filer's reported percent (often based on stale outstanding_basis)
- Document all differences

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
-- Get latest filing in chain
WITH RECURSIVE filing_chain AS (
  SELECT * FROM beneficial_filings WHERE accession_no = ?
  UNION
  SELECT bf.* FROM beneficial_filings bf
  JOIN filing_chain fc ON bf.amends_accession_no = fc.accession_no
)
SELECT * FROM filing_chain ORDER BY filing_date DESC LIMIT 1;
```

## Deliverables Structure

1. **Schema + Loader**: SQL tables and idempotent data loading script
2. **Six Queries**: Top holders, weekly activity, percentage reconciliation, watch list, temporal comparison, shares outstanding validation
3. **Monday Screen**: Interactive dashboard for CFO (Streamlit/HTML/notebook)
4. **Data Freshness Doc**: One-page engineer guide on keeping data current
5. **Fault List**: Documented data quality issues and handling approach

## Code Organization

- `src/schema.sql`: Table definitions with comprehensive comments
- `src/`: Loader scripts and query implementations
- `EDA/`: Exploratory analysis notebooks
- `data/`: Raw CSV files (read-only)
