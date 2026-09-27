# Query 4: Watch List - Decisions & Rationale

## Key Decisions

**1. Date Range - Event Date (When It Happened)**
- Filter: `event_date BETWEEN '2026-06-01' AND '2026-08-31'`
- This is when the threshold crossing or form change legally occurred
- `filing_date` shows when we learned about it (may be later)
- Both dates are shown in output for CFO transparency

**2. Chronological Comparison Method**
- Compare each filing to the **previous filing by event_date** (not amendment chains)
- Use window function: `LAG(percent_reported) OVER (PARTITION BY filer_cik ORDER BY event_date, filing_date)`
- Rationale: Detects actual position changes over time
- Example: If a filer has filings on June 15 (4%), July 10 (6%), Aug 20 (11%), compare each to the prior one chronologically

**3. First Filing Treatment**
- **Include first filings as crossings** if they're ≥5% or ≥10%
- Treat `prev_percent IS NULL` as starting from 0%
- Rationale: First disclosure above threshold is actionable intelligence for CFO
- Example: New filer appears with 8% position → Flag as "Crossed above 5%" AND "Crossed above 10%"

**4. Multiple Threshold Alerts**
- **Show all thresholds crossed in a single position change**
- If holder goes from 4% to 11%, show two alerts:
  - "Crossed above 5%"
  - "Crossed above 10%"
- Each appears as a separate row in the output
- Rationale: CFO needs to know about all significant thresholds crossed

**5. Threshold Detection Logic**

| Alert Type | Condition | Previous % | Current % |
|------------|-----------|------------|-----------|
| Crossed above 5% | Moved from <5% to ≥5% | <5.0 or NULL | ≥5.0 |
| Crossed below 5% | Moved from ≥5% to <5% | ≥5.0 | <5.0 |
| Crossed above 10% | Moved from <10% to ≥10% | <10.0 or NULL | ≥10.0 |
| Crossed below 10% | Moved from ≥10% to <10% | ≥10.0 | <10.0 |

**6. Form Type Change Detection (13G → 13D)**
- Detect when `prev_form LIKE '13G%'` and `form_type LIKE '13D%'`
- Uses pattern matching to catch 13G, 13G/A amendments
- **Key CFO Alert**: Indicates change from passive to activist investor
- Compare to previous chronological filing (not just amendment parent)
- Rationale: Any 13D following a 13G is a change in intent, regardless of amendment relationship

**7. Window Function Ordering**
- `ORDER BY event_date, filing_date` within each filer partition
- If two filings have same event_date, filing_date breaks the tie
- Ensures consistent "previous" filing identification

**8. Output Columns**

**Identification:**
- `filer_cik`: SEC filer identifier
- `filer_name`: Name of the filer

**Dates:**
- `date_happened`: event_date (when the position/form change legally occurred)
- `date_learned`: filing_date (when SEC received the form, when we learned about it)

**Alert Details:**
- `alert_type`: Type of watch list event
  - "Crossed above 5%"
  - "Crossed below 5%"
  - "Crossed above 10%"
  - "Crossed below 10%"
  - "Changed from 13G to 13D"

**Context for Threshold Crossings:**
- `previous_percent`: Percentage in prior filing (NULL for form changes)
- `current_percent`: Percentage in current filing (NULL for form changes)

**Context for Form Changes:**
- `previous_form`: Form type in prior filing (NULL for threshold crossings)
- `current_form`: Form type in current filing (NULL for threshold crossings)

**9. Data Source**
- Uses only `beneficial_filings` table
- Does not reconcile with register events
- Rationale: Watch list is based on SEC disclosures (public filings), not register positions

**10. Ordering**
- Primary: `event_date` (chronological order of when events happened)
- Secondary: `filing_date` (when we learned about events on same date)
- Tertiary: `filer_cik` (alphabetical by filer)
- Quaternary: `alert_type` (consistent ordering of multiple alerts)

## Edge Cases and Handling

**Case 1: Filer's First Filing at 8%**
- Triggers two alerts: "Crossed above 5%" and "Crossed above 10%"
- `previous_percent` = 0.0 (treated as coming from 0%)
- `current_percent` = 8.0
- Both date_happened and date_learned are from the first filing

**Case 2: Filer Goes from 4% to 11%**
- Triggers two alerts: "Crossed above 5%" and "Crossed above 10%"
- Two separate rows in output, same dates
- CFO sees both threshold crossings clearly

**Case 3: Filer Goes from 7% to 12%**
- Triggers one alert: "Crossed above 10%"
- Does NOT trigger "Crossed above 5%" (already above 5% in previous filing)

**Case 4: Filer Goes from 11% to 4%**
- Triggers two alerts: "Crossed below 10%" and "Crossed below 5%"
- Shows significant reduction in position

**Case 5: Filer Files 13G/A, Then 13D**
- Triggers: "Changed from 13G to 13D"
- Previous form shows "13G/A", current shows "13D"
- Indicates activist intent change

**Case 6: Same Event Date, Different Filing Dates**
- Window function uses `ORDER BY event_date, filing_date`
- Earlier filing_date is treated as "previous"
- Ensures deterministic comparison

## CFO Use Case

This query answers:
- **"Who's building a position?"** - Crossings above 5% or 10%
- **"Who's exiting?"** - Crossings below 5% or 10%
- **"Who became an activist?"** - 13G → 13D conversions (highest priority alert)
- **"When did it happen vs when did we learn?"** - Dual date columns show information lag

**Priority Levels for CFO:**
1. **Critical**: 13G → 13D change (activist intent)
2. **High**: Crossed above 10% or below 10% (major position change)
3. **Medium**: Crossed above 5% or below 5% (disclosure threshold)

**Example Use:**
CFO can filter by:
- `alert_type LIKE '%13D%'` for activist alerts
- `alert_type LIKE '%10%'` for major threshold crossings
- `date_learned > date_happened` to see delayed disclosures (potential late filings)
