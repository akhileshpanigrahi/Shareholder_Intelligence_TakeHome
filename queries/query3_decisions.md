# Query 3: Percent Reconciliation - Decisions & Rationale

## Key Decisions

**1. Analyze ALL Filings (Including Amendments)**
- Every filing in `beneficial_filings` table is analyzed
- Includes original 13D/13G and all amendments
- Rationale:
  - Shows reconciliation accuracy over time
  - Each filing represents a point-in-time regulatory snapshot
  - Amendments may occur on different dates with different positions
  - CFO needs to see if discrepancies are consistent or improve over time

**2. Date Selection - event_date and effective_date**
- **For SEC filings**: Use `event_date` (when the ownership position legally existed)
- **For register position calculation**: Use `effective_date <= event_date`
  - Calculates actual position as it existed on event_date
  - Matches the date the SEC filer was reporting about
  - Apples-to-apples comparison
- **NOT using filing_date or recorded_at**: Those show when we learned, not actual position

**3. Position Calculation Method - MAX Logic (like Query 1)**
For each filing's event_date, first compute filer's register position:
```
register_shares = opening_position (May 31)
                + SUM(transfers TO holder WHERE effective_date <= event_date)
                - SUM(transfers FROM holder WHERE effective_date <= event_date)
                - (exclude all reversed transfers)
```

Then apply MAX logic to get our best estimate:
```
our_shares = MAX(register_shares, shares_reported)
```

**Rationale:**
- **If register > SEC filing**: ERROR - direct holdings can't exceed total beneficial ownership
- **If SEC filing > register**: NORMAL - filer has indirect holdings via CEDE & CO
- **If register = SEC filing**: PERFECT - all holdings are direct

This matches Query 1 logic and avoids double-counting while highlighting true mismatches.

**4. Shares Outstanding Lookup**
- **For event_dates within data range**: Use most recent `shares_outstanding` where `as_of_date <= event_date`
  - Example: If event_date = 2026-07-15, use shares_outstanding from 2026-06-30
  - Assumption: Outstanding shares remain constant until next published update
- **For event_dates BEFORE first shares_outstanding record**: Use earliest available shares_outstanding
  - Example: If event_date = 2026-02-12 but first shares_outstanding is 2026-06-30, use 2026-06-30 value
  - Rationale: We carry the earliest known value backwards for historical filings
  - Assumption: Outstanding shares likely similar to later reported value
  - This handles SEC filings that occurred before our shares_outstanding data begins
- This is the "actual" denominator for percentage calculation

**5. Handling Unmapped Filers**
- Some SEC filers have no `holder_id` in `holder_filer_mapping`
- These are beneficial owners behind CEDE with no direct register position
- Set `our_shares = 0` for these filers
- Explanation column: "No register position - beneficial owner behind CEDE"

**6. Reversal Exclusion**
- Exclude all transfers where `transfer_id IN (SELECT reverses_transfer_id ...)`
- Same logic as Query 1 and 2
- Ensures position calculations reflect net reality

**7. Output Columns**

**Identification:**
- `filer_cik`, `filer_name`: Who filed
- `event_date`: When the position legally existed
- `filing_date`: When SEC received the form
- `accession_no`: Unique filing identifier
- `form_type`: 13D, 13D/A, 13G, 13G/A
- `amends_accession_no`: If this filing amends another

**Reported Values (from SEC filing):**
- `shares_reported`: What filer claimed to hold
- `percent_reported`: What filer calculated
- `outstanding_basis`: Denominator filer used

**Our Computed Values:**
- `our_shares`: MAX(register_shares, shares_reported) - our best estimate
- `actual_outstanding`: True shares outstanding on event_date
- `our_percent`: Our calculation (our_shares / actual_outstanding * 100)

**Variance Analysis:**
- `percent_diff`: our_percent - percent_reported
- `explanation`: Simple Match/Mismatch with reason

**8. Simplified Explanation Logic**

The `explanation` column provides clear Match/Mismatch categorization:

| Condition | Explanation | Meaning |
|-----------|-------------|---------|
| register = SEC, outstanding correct, % within 0.01% | "Match" | Perfect reconciliation |
| register > SEC | "Mismatch: Register exceeds SEC filing" | **ERROR** - impossible scenario |
| register = SEC, but stale outstanding | "Mismatch: Stale outstanding basis" | Filer used wrong denominator |
| register < SEC, outstanding correct | "Match: Indirect holdings via CEDE" | Normal - filer has shares behind CEDE |
| register < SEC, stale outstanding | "Match: Indirect via CEDE, but stale basis" | Normal position, wrong denominator |
| register = SEC, outstanding correct, minor % diff | "Match: Minor rounding difference" | Calculation precision |
| Other | "Review needed" | Edge case requiring investigation |

**9. Rounding Tolerance**
- Allow 0.01% tolerance for "Match" determination
- Handles minor calculation/rounding differences
- Example: 5.00% vs 5.01% = Match
- Example: 5.00% vs 5.10% = Variance

**10. Ordering**
- Primary: `filer_cik` (group same filer together)
- Secondary: `event_date` (chronological within filer)
- Shows progression of each filer's filings over time

## Data Assumptions and Limitations

**Shares Outstanding Data Coverage:**
- Our `shares_outstanding` table has limited historical data
- For filings with event_dates before our data range, we use earliest available value
- This is documented in the query with COALESCE logic
- CFO should be aware that historical reconciliations use projected outstanding shares

**Register Events Coverage:**
- Opening positions start from 2026-05-31
- Register events cover 2026-06-01 to 2026-08-31
- Filings with event_dates before May 31 will show our_shares = 0 (before our data)
- This is correct behavior - we can't reconstruct positions before our data begins

## Common Patterns Explained

**1. Match: Indirect holdings via CEDE (Most Common)**
- SEC filing shows more shares than register
- **This is NORMAL and expected**
- Filer holds shares through broker (street name), hidden in CEDE & CO line
- We accept SEC filing as source of truth
- Example: Register shows 0, SEC shows 2.5M → our_shares = 2.5M (MAX logic)

**2. Match: Perfect reconciliation**
- Register position = SEC filing
- Outstanding basis is current
- Percentage within 0.01% tolerance
- All holdings are direct (not through CEDE)

**3. Mismatch: Stale outstanding basis**
- Filer uses outdated shares_outstanding number
- Position matches but percentage differs
- Example: 5M shares / 100M basis = 5.00% reported
  - But actual outstanding = 102M
  - Our calc: 5M / 102M = 4.90%

**4. Mismatch: Register exceeds SEC filing (ERROR - Investigate!)**
- Direct holdings on register > total beneficial ownership reported to SEC
- **This should not happen** - impossible scenario
- Indicates data quality issue requiring investigation
- Example: Register shows 3M, SEC shows 2.5M → flag for review

## CFO Use Case
This query answers:
- "Do our register positions reconcile with SEC filings?"
- "Which filings show true mismatches vs normal indirect holdings?"
- "Are there any impossible scenarios (register > SEC) that need investigation?"
- "Which filers are using stale outstanding share counts?"
- "What's our visibility into holdings behind CEDE & CO?"

**Key Insight:** Most "Match: Indirect via CEDE" results are GOOD - they show the system working correctly. Only "Mismatch: Register exceeds SEC" requires immediate attention.
