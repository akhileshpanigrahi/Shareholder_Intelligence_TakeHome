# Query 2: Weekly Activity - Decisions & Rationale

## Key Decisions

**1. Date Filters**
- **Effective date**: `BETWEEN '2026-08-24' AND '2026-08-28'`
  - The week being analyzed (Mon-Fri before the Monday report)
  - Uses legal transaction date (when it actually happened)
- **Recorded at**: `<= '2026-08-31 16:00:00'`
  - Query runs on Monday Aug 31 at 4 PM after market close
  - Includes all events known to the system by that time
  - Late-recorded events from the week are captured

**2. Holder Type Assignment - Option A (End of Period)**
- Use holder_type **as of Aug 31** for ALL transactions
- Rationale: CFO wants to know "which current holder types were active"
- Example: If H005 changed from "individual" to "insider" on Aug 26:
  - ALL their Aug 24-28 transactions count under "insider"
  - Provides clearer picture of current ownership composition
- Alternative (rejected): Use holder_type at time of each transaction
  - Would split same holder across multiple types
  - Less actionable for CFO's Monday review

**3. Handling NULL Holders (Issuance/Buyback)**
- `to_holder_id IS NULL` → share buyback (company retired shares)
  - Count only the `from_holder_id` (who sold to company)
- `from_holder_id IS NULL` → equity issuance (company issued new shares)
  - Count only the `to_holder_id` (who received new shares)
- Rationale: CFO cares about shareholder activity, not company treasury operations

**4. CEDE & CO Inclusion**
- **Included** CEDE (H001) in the results
- Rationale: Material movements to/from CEDE indicate:
  - Shares moving from direct registration to street name (or vice versa)
  - Important signal for CFO about registration patterns
- CEDE activity is legitimate shareholder movement, not noise

**5. Reversal Handling**
- Excluded all transfers with `reverses_transfer_id IS NOT NULL`
- Same logic as Query 1: reversals net to zero
- Example: If T5189 was reversed, exclude the original transfer

**6. Aggregation Level**
- **Aggregated by holder_type** (not individual holders)
- Shows institutional vs individual vs insider activity patterns
- Provides strategic view rather than tactical detail

**7. Output Columns**
- **holder_type**: Type of holder (institution, individual, insider, nominee, trust)
- **shares_bought**: Total shares acquired during the week
- **shares_sold**: Total shares disposed during the week
- **net_change**: Net position change (positive = net buyer, negative = net seller)

**8. Excluded Columns**
- **Transaction count**: Not included
  - Rationale: CFO cares about magnitude (shares), not frequency
  - One large institutional buy is more meaningful than many small trades

**9. Zero Activity Exclusion**
- Only show holder types with activity (bought OR sold > 0)
- Empty types add no value to CFO's Monday screen
- Keeps report focused on actionable information

**10. Ordering**
- Alphabetical by `holder_type`
- Provides consistent, predictable ordering
- Alternative (rejected): Order by net_change magnitude
  - Less stable week-to-week, harder to compare

## Run Context
- Query execution: Monday, August 31, 2026 at 16:00
- Analysis period: August 24-28, 2026 (previous trading week)
- All transactions known to system by Monday 4 PM are included

## CFO Use Case
This query answers: "What types of investors were active last week?"
- Net buyers by type → confidence signal
- Net sellers by type → concern trigger
- Shifts between types → ownership composition changes
