# Query 5: Sable Point Temporal Comparison - Decisions & Rationale

## Key Decisions

**1. Target Date - July 31, 2026**
- Calculate Sable Point Advisors (H011) register position as of July 31, 2026
- Compare two perspectives of the SAME date:
  - "As we knew it on July 31" (system view then)
  - "As we know it today" (system view now with Sept 1, 2026 knowledge)

**2. "Today" Definition - September 1, 2026**
- Assumption: Query runs on September 1, 2026 (after all data in the system)
- Use `recorded_at <= '2026-09-01 23:59:59'` for current knowledge cutoff
- Rationale: All register events and reversals through Aug 31 are recorded by Sept 1

**3. Position Calculation - Simplified Pattern**

**Position "as we knew it on July 31, 2026":**
```sql
Opening position (May 31)
+ Transfers TO H011 WHERE effective_date <= '2026-07-31'
                     AND recorded_at <= '2026-07-31 23:59:59'
                     AND event_type != 'reversal'
- Transfers FROM H011 WHERE effective_date <= '2026-07-31'
                       AND recorded_at <= '2026-07-31 23:59:59'
                       AND event_type != 'reversal'
```

**Position "as we know it today" (Sept 1, 2026):**
```sql
Opening position (May 31)
+ Transfers TO H011 WHERE effective_date <= '2026-07-31'
                     AND recorded_at <= '2026-09-01 23:59:59'
                     -- Include ALL event types (transfer and reversal)
- Transfers FROM H011 WHERE effective_date <= '2026-07-31'
                       AND recorded_at <= '2026-09-01 23:59:59'
                       -- Include ALL event types (transfer and reversal)
```

**4. Reversal Handling - Event Type Based**

**"As we knew it" view (July 31):**
- Exclude events where `event_type = 'reversal'` AND `recorded_at <= '2026-07-31'`
- This excludes reversal transactions that we knew about by July 31
- Original transfers are included (even if later reversed, we didn't know yet)
- **Rationale:** On July 31, we only exclude reversals we knew about at that time

**"As we know it" view (Sept 1):**
- Include ALL events (both 'transfer' and 'reversal' types)
- Natural netting occurs: original transfer (+shares) minus reversal (-shares)
- **This is the key difference:** We now include reversal events recorded after July 31
- For partial reversals, this correctly nets: +1,650,000 (original) - 400,000 (reversal) = +1,250,000

**Why this approach:**
- Reversal events are modeled as opposite-direction transfers (e.g., H011→H001 reverses H001→H011)
- For partial reversals, excluding the original transfer entirely would lose the unreverted portion
- Including both and letting them net naturally handles both full and partial reversals correctly

**5. Sable Point Holder Identification**
- Holder ID: H011
- Latest holder name: "Sable Point Advisors LLC"
- Filer CIK: 3344556
- Opening position (May 31): 0 shares

**6. Output Format - Single Row**
- One row showing both perspectives side-by-side
- Columns:
  - `holder_id`: H011
  - `holder_name`: Sable Point Advisors LLC
  - `as_of_date`: 2026-07-31 (the date we're analyzing)
  - `position_then`: Shares as we knew it on July 31
  - `position_now`: Shares as we know it today (Sept 1)
  - `difference`: position_now - position_then
  - `explanation`: Human-readable explanation of the difference
  - `late_events_detail`: Detailed list of events recorded after July 31 that changed our view

**7. Late Events Identification**

The query identifies two types of "late" events:

1. **Events recorded after July 31** with effective_date <= July 31:
   - These are events that happened on/before July 31 but we learned about later
   - Example: A transfer on July 28 recorded on Aug 6

2. **Original transfers that were reversed after July 31**:
   - Transfers recorded before/on July 31
   - But reversed by events recorded after July 31
   - On July 31, we counted these transfers (didn't know about reversal yet)
   - By Sept 1, we exclude these transfers (now know they were reversed)

**8. Explanation Logic**

```
IF difference = 0:
  "No change - positions match"

IF difference < 0:
  "Position decreased by [amount] shares due to late-recorded reversal(s) after July 31"

IF difference > 0:
  "Position increased by [amount] shares due to late-recorded event(s) after July 31"
```

**9. Data Scope**
- Uses only `register_events` and `opening_positions` tables
- Does NOT use SEC filings (this is pure register analysis)
- Filters to Sable Point Advisors (H011) only

## Expected Result Based on Data

**Sable Point Register Events:**

| Event | Transfer | Type | Shares | Effective Date | Recorded At | Reverses | Note |
|-------|----------|------|--------|----------------|-------------|----------|------|
| E1180 | T5181 | transfer | +2,100,000 | 2026-07-07 | 2026-07-07 11:20 | - | DRS withdrawal |
| E1181 | T5182 | transfer | +1,650,000 | 2026-07-28 | 2026-07-28 16:40 | - | DRS withdrawal |
| E1187 | T5188 | reversal | -400,000 | 2026-07-28 | 2026-08-06 17:55 | T5182 | Partial reversal - broker over-delivered |

**Position "as we knew it on July 31, 2026":**
- Opening: 0
- +2,100,000 (E1180, T5181, recorded July 7, event_type='transfer') ✅ included
- +1,650,000 (E1181, T5182, recorded July 28, event_type='transfer') ✅ included
- E1187 reversal excluded (event_type='reversal', recorded Aug 6, after July 31)
- **Total: 3,750,000 shares**

**Position "as we know it today" (Sept 1, 2026):**
- Opening: 0
- +2,100,000 (E1180, T5181, recorded July 7, event_type='transfer') ✅ included
- +1,650,000 (E1181, T5182, recorded July 28, event_type='transfer') ✅ included
- -400,000 (E1187, T5188, recorded Aug 6, event_type='reversal') ✅ now included
- **Total: 0 + 2,100,000 + 1,650,000 - 400,000 = 3,350,000 shares**

**Difference: 3,350,000 - 3,750,000 = -400,000 shares**

**Explanation:**
"Position decreased by 400,000 shares due to late-recorded reversal(s) after July 31"

**Late Events Detail:**
- E1187 (reversal): 400,000 shares, effective July 28, recorded Aug 6 - the late-recorded reversal
- E1181 (transfer): 1,650,000 shares, effective July 28, recorded July 28 - the original transfer that was later partially reversed

Note: E1181 appears in late_events not because it was recorded late, but because it was affected by a late-recorded reversal (E1187). This provides context to understand what transaction was being reversed.

## Key Insight for CFO

This query demonstrates **why temporal tracking matters**:

1. **On July 31**, the CFO believed Sable Point had **3.75M shares** on the register
2. **By September 1**, we learned that a broker over-delivered 400K shares on July 28
3. **The reversal** (E1187) was recorded on August 6, correcting the error
4. **Actual position on July 31** was **3.35M shares**, not 3.75M

**Business Impact:**
- If CFO made decisions based on July 31 data (e.g., ownership thresholds, voting rights), those decisions were based on inflated numbers
- Late reversals can change historical positions retroactively
- This is why "as of" reporting must distinguish between knowledge date and effective date

**Data Quality Signal:**
- A 9-day lag (July 28 → August 6) for a same-day reversal indicates process issues
- Ideally, reversals should be recorded on the same day as the error is detected
