# Query 1: Top Holders - Decisions & Rationale

## Key Decisions

**1. Excluded CEDE & CO (H001)**
- CEDE is a nominee holding ~33M shares on behalf of brokers/beneficial owners
- Not a "real owner" - actual owners behind CEDE appear in SEC filings
- Including CEDE would distort top 10 list

**2. Date Filters - System View vs Actual Position**
- **Register shares column**: `recorded_at <= '2026-08-31'`
  - Shows what was in the system on Aug 31
  - Reflects the data CFO would have seen that day
- **SEC shares column**: `filing_date <= '2026-08-31'`
  - SEC filings received by Aug 31
  - System view of reported ownership
- **Best estimate column**: `effective_date` (register) + `event_date` (SEC)
  - True legal ownership position on Aug 31
  - Corrects for late-recorded reversals and backdated events

**3. Reversed Transfers**
- Excluded all transfers with `reverses_transfer_id IS NOT NULL`
- Reversals net to zero and should not affect position calculations
- Example: Transfer T5189 (12k shares, Aug 27) was reversed Sept 2

**4. Amendment Chain Resolution**
- Followed `amends_accession_no` to get latest SEC filing per filer
- Example: Ridgeline filing 101 amended by filing 188 → use 188
- Ensures we show current disclosed position, not stale data

**5. Best Estimate Logic - MAX Not SUM**
- When holder appears in both register AND SEC: `MAX(register, SEC)`
- Rationale: SEC filing reports TOTAL beneficial ownership including direct holdings
- Example: If Ridgeline has 2.9M direct + SEC reports 4.3M total → 4.3M, not 7.2M
- Avoids double-counting shares

**6. Identity Reconciliation**
- Created `holder_filer_mapping` to link holder_id ↔ filer_cik
- Handles name variations (e.g., "Halvard Holdings LLC" vs "Halvard Office LLC")
- Used latest holder version for name changes

**7. Handling Unmapped SEC Filers**
- Filers without holder_id mapping (e.g., Vantage Quant Strategies) included
- These are beneficial owners behind CEDE with no direct register presence
- Register shares = 0, SEC shares from filing, best estimate = SEC shares

## Run Date Assumption
- Query assumes execution on September 1, 2026 00:00
- "As of Aug 31" means all data through end of day Aug 31
