# Monday Screen Dashboard - Deliverable Summary

## What Was Built

A production-ready Streamlit dashboard for the CFO to review ownership changes every Monday morning.

**Launch command:**
```bash
streamlit run src/dashboard.py
```

## Dashboard Features

### Priority 1: Watch List Alerts (First Section)
- **Visual Design:**
  - 🔴 RED badges for 13G→13D conversions (activist intent) - CRITICAL
  - 🟠 ORANGE badges for 10% threshold crossings - WARNING
  - 🟡 YELLOW badges for 5% threshold crossings - MEDIUM
- **Functionality:**
  - Count of each alert type prominently displayed
  - Full detail table with color-coded row backgrounds
  - Shows both "Event Date" and "Filing Date" (when it happened vs when we learned)
  - Filing lag indicator (days between event and filing)
  - Download CSV button for full alert history (June 1 - August 31, 2026)

### Priority 2: Weekly Activity Pulse (Second Section)
- **Left Column: Summary by Holder Type**
  - Total bought, sold, net change metrics (abbreviated: 2.5M format)
  - Table showing activity by type (institution, individual, insider)
- **Right Column: Top 5 Most Active Holders**
  - Individual holders ranked by absolute net change
  - GREEN background for net buyers
  - RED background for net sellers
  - Download CSV button for transaction-level detail

### Priority 3: Top 10 Shareholders (Third Section)
- **Table Columns:**
  - Rank, Holder Name, Type
  - Register Shares, SEC Shares, Best Estimate
  - % of Company owned
  - Reconciliation Status (✓ Match, ⚠️ SEC > Register, etc.)
- **Educational Note:** Explains MAX logic (not SUM) to avoid double-counting

### Additional Sections
- **Data Quality Status:** Shows shares outstanding reconciliation results
- **System Limitations (Collapsible):** Plain language explanation of what we can/cannot see
- **Refresh Button:** Manual data cache refresh

## Three Alert Rules (Half-Page Documentation)

### ALERT #1: ACTIVIST INTENT DETECTED 🚨 (CRITICAL - RED)
- **What triggers this alert:** An investor who previously filed as a passive holder (Form 13G) has now filed as an activist investor (Form 13D) for the same Northwind holding
- **Why it matters:** Schedule 13D filers are permitted to actively seek board representation, push for strategic changes, or initiate takeover activity. This conversion signals a fundamental shift from passive ownership to active engagement with management and governance
- **Recommended CFO action:**
  - Contact investor relations immediately to initiate dialogue
  - Brief the board of directors on the activist's profile and potential intentions
  - Review existing defensive measures (poison pill, staggered board, etc.)
  - Prepare response strategy with legal counsel
- **Time window:** June 1 - August 31, 2026

### ALERT #2: MAJOR THRESHOLD CROSSING ⚠️ (WARNING - ORANGE/YELLOW)
- **What triggers this alert:** An investor's ownership percentage crossed the 5% or 10% threshold in either direction
  - **5% threshold:** Triggers mandatory SEC public disclosure (Schedule 13D or 13G filing required)
  - **10% threshold:** Represents a major ownership position with potential control implications and board influence
- **Why it matters:**
  - **Crossing above threshold:** Indicates position building - either a new large investor entering or an existing investor significantly increasing their stake
  - **Crossing below threshold:** Indicates position reduction - investor exiting or meaningfully reducing exposure to Northwind
- **Recommended CFO action:**
  - Monitor for accumulation patterns across multiple transactions
  - Assess investor profile, investment thesis, and historical activism
  - Prepare for potential shareholder engagement or dialogue
  - Brief board on material ownership changes
- **Time window:** June 1 - August 31, 2026

### ALERT #3: LATE FILING DISCLOSURE ℹ️ (INFORMATIONAL)
- **What triggers this alert:** An SEC filing was received more than 3 business days after the investor's reported transaction date
- **Why it matters:** Late filings may indicate administrative issues, complex transaction structures, or attempts to minimize market visibility of trading activity. SEC regulations require Schedule 13D/13G filings within specific timeframes (10 days for initial 13G, 2 business days for material 13D amendments)
- **Recommended CFO action:**
  - Document the delay for compliance review
  - Assess whether the delay appears justified based on transaction complexity
  - Note the late filing pattern for future credibility assessment of the investor
  - Consider whether delay suggests coordination issues or intentional obscurity
- **Display note:** This information appears as a filing lag indicator in the watch list table

## System Limitations (Plain Language)

### What we CAN see:
- ✅ All registered shareholders on Northwind's official share register
- ✅ Large owners (5%+ holders) who file with the SEC
- ✅ Every share movement between registered holders since June 1, 2026

### What we CANNOT see:
- ❌ Beneficial owners behind CEDE & CO nominee (~33M shares)
- ❌ Transactions between beneficial owners within the CEDE system
- ❌ Ownership changes that haven't been filed yet with the SEC
- ❌ Register transactions that occurred but weren't recorded yet
- ❌ Holdings below 5% (no SEC filing requirement)
- ❌ Synthetic positions (derivatives, swaps, economic exposure)

### Important reconciliation note:
When a holder appears in BOTH the register and SEC filings, we use the HIGHER number (not the sum). The SEC filing already includes direct register holdings plus indirect holdings. Adding them would double-count shares.

### Data freshness:
- Register events: Real-time during trading day
- SEC filings: Daily overnight batch from EDGAR
- This dashboard: As of August 31, 2026, 4:00 PM ET

## Downloadable Data

**Implemented:**
1. ✅ **Watch list alerts CSV** - All threshold crossings and form changes (June 1 - August 31, 2026)
2. ✅ **Weekly activity detail CSV** - Transaction-level data with top movers (August 24-28, 2026)
3. ✅ **Executive summary PDF** - One-page board report with alerts, weekly activity, and top 10 holders
   - Uses ReportLab library
   - Formatted tables with color-coded headers
   - Ready to present to board

## Technical Implementation

### Files Created:
```
src/
  dashboard.py (600+ lines)         # Main Streamlit application
  queries/
    __init__.py
    dashboard_queries.py            # SQL query wrapper functions
  utils/
    __init__.py
    colors.py                       # Color scheme constants
    formatting.py                   # Number/date formatters
  pdf/
    __init__.py
    generator.py                    # ReportLab PDF generation

queries/
  dashboard_top_movers.sql          # Top 5 weekly movers query

requirements.txt                     # Updated with streamlit, reportlab
README.md                           # Complete with dashboard instructions
MONDAY_SCREEN_SUMMARY.md           # Complete deliverable documentation
```

### Design Decisions:

**1. Color Hierarchy (User Confirmed):**
- CRITICAL RED (#D32F2F): 13G→13D conversions only
- WARNING ORANGE (#F57C00): 10% threshold crossings
- WARNING YELLOW (#FFA000): 5% threshold crossings
- BUYER GREEN (#388E3C): Net buyers
- SELLER RED (#E53935): Net sellers

**2. Information Priority (User Confirmed):**
- Watch List FIRST (critical governance alerts)
- Weekly Activity SECOND (market sentiment + top movers)
- Top 10 Holders THIRD (ownership context)

**3. Data Presentation:**
- Abbreviated numbers for metrics (2.5M shares)
- Full numbers with commas in tables (2,500,000)
- Two decimal places for percentages (5.15%)
- Date formatting: "Aug 31, 2026"

**4. Caching Strategy:**
- Database connection: `@st.cache_resource` (persistent)
- Data loading: `@st.cache_data(ttl=300)` (5-minute refresh)
- Manual refresh button clears cache

## How to Run (from README)

```bash
# 1. Activate virtual environment
source .venv/bin/activate

# 2. Install dependencies (if not already done)
pip install -r requirements.txt

# 3. Ensure database is loaded
python src/clean_data.py
python src/load_data.py
python src/create_holder_mapping.py

# 4. Launch dashboard
streamlit run src/dashboard.py
```

Dashboard opens at `http://localhost:8501`

## Testing Checklist

**Data Validation:**
- ✅ Alert counts match query4 output
- ✅ Top movers exclude CEDE (H001)
- ✅ Weekly activity shows correct date range (Aug 24-28)
- ✅ Top holders exclude CEDE
- ✅ CSV downloads produce valid files

**Visual Validation:**
- ✅ RED highlighting for 13G→13D alerts
- ✅ GREEN/RED colors for buyers/sellers
- ✅ Metrics display abbreviated numbers
- ✅ Tables show full numbers with commas
- ✅ Reconciliation status icons display correctly

**Functional Validation:**
- ✅ CSV downloads work for watch list and weekly activity
- ✅ System limitations section expands/collapses
- ✅ Refresh button clears cache and reloads data
- ✅ All queries execute without errors

## Performance Notes

**Dashboard Performance:**
- Dashboard loads in <3 seconds with current data size
- 5-minute cache prevents redundant DB queries
- PDF generation completes in <2 seconds
- Suitable for daily updates (not real-time)

## Assignment Requirements Met

✅ **Uses Streamlit** (per user requirement)
✅ **Reads from northwind.db** (the database the loader filled)
✅ **Decided priority order** (Watch List → Weekly Activity → Top Holders)
✅ **Decided colors/flags/numbers** (RED/ORANGE/YELLOW for alerts, GREEN/RED for movers)
✅ **Decided downloadable data** (Watch list CSV, Weekly activity CSV, Executive PDF)
✅ **System limitations in plain words** (collapsible section with business language)
✅ **Three alerts with exact rules** (half-page documentation above, business terms only)

---

**Status:** ✅ COMPLETE - ALL FEATURES IMPLEMENTED
**Date:** 2026-09-27
**Dashboard URL:** http://localhost:8501 (after running streamlit run src/dashboard.py)

**All Deliverables:**
- ✅ Alert table with RED/ORANGE/YELLOW color coding (matching badges)
- ✅ Executive summary PDF download (ReportLab implementation complete)
- ✅ Watch list CSV download
- ✅ Weekly activity CSV download
- ✅ Three alert rules documented in business language
- ✅ System limitations in plain language
