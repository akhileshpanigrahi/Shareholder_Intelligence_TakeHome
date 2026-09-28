# Data Freshness & Integrity - Engineering Guide

**One-page reference for maintaining dashboard accuracy**

---

## 1. Data Pipeline: Register → Dashboard

### Current State
- Manual execution: `python src/clean_data.py && python src/load_data.py && python src/create_holder_mapping.py`
- Dashboard reads from static SQLite database (northwind.db)
- No automated refresh

### Recommended Architecture

**Register Events (Intraday):**
- **Source:** register_events.csv appended throughout trading day
- **Update frequency:** Continuous append or hourly batch
- **Pipeline:**
  - Incremental load: `INSERT new events WHERE event_id NOT IN (SELECT event_id FROM register_events)`
  - Skip clean_data.py (only needed for historical duplicates)
  - Update holder_filer_mapping if new holder_id detected
- **Latency:** 5-15 minutes from CSV append to dashboard refresh

**SEC Filings (Daily):**
- **Source:** beneficial_filings.csv updated overnight (EDGAR batch)
- **Update frequency:** Once daily, 6:00 AM ET
- **Pipeline:**
  - Full reload: `DELETE FROM beneficial_filings; INSERT new data`
  - Rebuild holder_filer_mapping (fuzzy matching may find new links)
- **Latency:** Available by 6:30 AM ET

**Dashboard Cache:**
- Streamlit `@st.cache_data(ttl=300)` refreshes every 5 minutes
- Manual refresh button: `st.cache_data.clear()` forces immediate reload
- **Effective latency:** Max 5 minutes after database update

---

## 2. Late Reversals: Impact on Historical Views

### Scenario
- Aug 26 (Tuesday): Transfer T1234 records +100,000 shares (effective_date = Aug 26, recorded_at = Aug 26)
- Sept 1 (Monday): Reversal discovered, reversal event created (effective_date = Aug 26, recorded_at = Sept 1)

### Dashboard Behavior

**Queries use `effective_date` for filtering:**
- Position calculations: `WHERE effective_date <= '2026-08-31'` (includes both original and reversal)
- Reversals are excluded via: `WHERE transfer_id NOT IN (SELECT reverses_transfer_id FROM register_events WHERE reverses_transfer_id IS NOT NULL)`
- **Result:** Reversal retroactively corrects the Aug 26 position

**Impact:**
- Historical exports change when reversal arrives
- Aug 28 report exported before Sept 1: showed +100,000 (incorrect)
- Same Aug 28 report exported after Sept 1: shows +0 (corrected)
- **No point-in-time "what we knew then" view** - dashboard always shows legal reality

**Exception - Query 5 (Temporal Comparison):**
- Demonstrates both views using `recorded_at` filter
- `recorded_at <= '2026-07-31'`: excludes reversals recorded after July 31
- Used for auditing, not standard dashboard operation

---

## 3. "As of" Date Semantics

### Definition
**"Week ending August 31, 2026"** means:
- **Effective date filter:** `effective_date <= '2026-08-31'` (when transactions legally occurred)
- **Knowledge cutoff:** No restriction on `recorded_at` (includes late-recorded events)
- **Interpretation:** Legal ownership reality as of Aug 31, using all information available today

### Examples

**Top Holders (Aug 31):**
- Includes: Transfer on Aug 20, recorded Sept 2 (late recording)
- Excludes: Transfer on Sept 3, recorded Sept 3 (after cutoff)

**Watch List (June 1 - Aug 31):**
- Uses `event_date <= '2026-08-31'` from beneficial_filings
- Shows when threshold crossings occurred, not when we learned about them
- `filing_date` displayed separately to show disclosure lag

### Edge Cases
- **Backdated corporate actions:** Use effective_date even if recorded weeks later
- **SEC filing amendments:** Use latest amendment's event_date (chronological, not amendment chain)
- **Reversals:** Applied to effective_date, not recorded_at date

---

## 4. Staleness Detection & Validation

### Automated Checks (Recommended)

**Pipeline health:**
```sql
-- Last register event recorded
SELECT MAX(recorded_at) FROM register_events;
-- Alert if > 2 hours old during trading hours (9:30 AM - 4:00 PM ET)

-- Last SEC filing loaded
SELECT MAX(filing_date) FROM beneficial_filings;
-- Alert if < yesterday's date (EDGAR publishes T-1)
```

**Data integrity:**
```sql
-- Shares outstanding reconciliation (Query 6)
SELECT
  (opening + equity_issued - buybacks) - reported_outstanding as variance
FROM shares_outstanding_validation;
-- Alert if variance != 0
```

**Row count monitoring:**
```python
# Track daily increments
assert len(new_events) > 0, "No new register events loaded"
assert len(new_filings) >= 0, "Beneficial filings count decreased"
```

### Dashboard Indicators

**Current implementation:**
- Manual refresh button visible (user-driven staleness detection)
- Cache TTL = 5 minutes (automatic refresh)
- Generation timestamp: `Generated: 2026-09-01 02:35 PM ET`

**Recommended additions:**
- Last data update timestamp: "Data as of: Sept 1, 2026 6:15 AM ET"
- Validation status badge: ✅ "Register reconciled" or ⚠️ "Discrepancy detected"
- Row counts: "Showing 145 events from Aug 24-28"

### Failure Modes

| Failure | Symptom | Detection |
|---------|---------|-----------|
| load_data.py fails | Empty tables or old data | Row count = 0 or MAX(recorded_at) stale |
| CSV corrupted | Pandas read error | Try/catch in loader, exit code != 0 |
| Fuzzy matching fails | holder_filer_mapping empty | Row count < expected minimum (e.g., < 5) |
| Dashboard cache stuck | Old timestamp shown | Compare "Generated" time to current time |
| Database locked | SQLite error | Connection timeout, dashboard shows error |

### Monitoring Stack (Recommended)
- Cron job: Daily 6:30 AM ET runs validation queries
- Alerting: Email/Slack if checks fail
- Logging: ETL pipeline logs to file with timestamps
- Metrics: Track load duration, row counts, cache hit rate

---

**End of document**
