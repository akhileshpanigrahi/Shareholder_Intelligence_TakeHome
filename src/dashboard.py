"""
Northwind Metals Corp - Monday Morning Ownership Intelligence Dashboard

CFO-focused executive dashboard showing:
1. Critical governance alerts (13G→13D conversions, threshold crossings)
2. Weekly trading activity by holder type and top movers
3. Top 10 shareholders with reconciled positions

Date: Monday, August 31, 2026
Data sources: Share register + SEC 13D/13G filings
"""

import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from src.queries.dashboard_queries import DashboardQueries
from src.utils.formatting import (
    format_shares,
    format_percent,
    format_shares_abbreviated,
    format_date,
    format_delta,
    format_reconciliation_status
)
from src.utils.colors import (
    CRITICAL_RED,
    WARNING_ORANGE,
    WARNING_YELLOW,
    BUYER_GREEN,
    SELLER_RED,
    get_alert_background
)
from src.pdf.generator import generate_executive_pdf

# Page configuration
st.set_page_config(
    page_title="Northwind Ownership Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for styling
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #1976D2;
    }
    .critical-alert {
        border-left-color: #D32F2F !important;
    }
    .warning-alert {
        border-left-color: #F57C00 !important;
    }
    .stMetric {
        background-color: white;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    /* PRIORITY 1: Make alert section visually dominant */
    .alert-section-header {
        font-size: 2.5em !important;
        font-weight: 800 !important;
        color: #D32F2F;
        margin-top: 2em;
        margin-bottom: 0.5em;
        padding: 20px;
        background-color: #FFF3E0;
        border-left: 10px solid #D32F2F;
        border-radius: 5px;
    }
    .alert-section-box {
        padding: 30px;
        background-color: #FFF8F0;
        border: 3px solid #F57C00;
        border-radius: 10px;
        margin-bottom: 40px;
    }
</style>
""", unsafe_allow_html=True)


# Database connection and query executor
@st.cache_resource
def get_query_executor():
    """Initialize database query executor (cached)."""
    return DashboardQueries()


# Data loading with caching
@st.cache_data(ttl=300)  # 5-minute cache
def load_dashboard_data():
    """Load all dashboard data from database."""
    queries = get_query_executor()

    return {
        'alert_summary': queries.get_alert_summary(),
        'watch_list': queries.get_watch_list(),
        'weekly_activity': queries.get_weekly_activity(),
        'top_movers': queries.get_top_movers(),
        'top_holders': queries.get_top_holders(),
        'shares_outstanding': queries.get_shares_outstanding_validation()
    }


def main():
    """Main dashboard application."""

    # Load all data
    data = load_dashboard_data()

    # =======================
    # SECTION 1: HEADER
    # =======================
    st.title("📊 Northwind Metals Corp - Monday Ownership Report")
    col_date, col_refresh = st.columns([4, 1])

    with col_date:
        st.caption(f"**Week ending August 31, 2026** | Generated: {datetime.now().strftime('%Y-%m-%d %I:%M %p ET')}")

    with col_refresh:
        if st.button("🔄 Refresh Data"):
            st.cache_data.clear()
            st.rerun()

    # =======================================
    # SECTION 2: CRITICAL ALERTS (Priority 1)
    # =======================================
    st.markdown("<br><br>", unsafe_allow_html=True)  # Extra spacing
    st.markdown('<div class="alert-section-box">', unsafe_allow_html=True)
    st.caption("**Critical governance events requiring board attention (June 1 - August 31, 2026)**")

    # Alert count badges
    alert_summary = data['alert_summary']
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        activist_count = alert_summary['activist_alerts']
        st.metric(
            label="🔴 ACTIVIST INTENT (13G→13D)",
            value=activist_count,
            delta="CRITICAL" if activist_count > 0 else "None",
            delta_color="inverse" if activist_count > 0 else "off"
        )

    with col2:
        threshold_10_count = alert_summary['threshold_10_alerts']
        st.metric(
            label="🟠 10% Threshold Crossings",
            value=threshold_10_count,
            delta="High Priority" if threshold_10_count > 0 else "None",
            delta_color="off"
        )

    with col3:
        threshold_5_count = alert_summary['threshold_5_alerts']
        st.metric(
            label="🟡 5% Threshold Crossings",
            value=threshold_5_count,
            delta="Medium Priority" if threshold_5_count > 0 else "None",
            delta_color="off"
        )

    with col4:
        late_filing_count = alert_summary['late_filing_alerts']
        st.metric(
            label="ℹ️ Late Filings (>5 days)",
            value=late_filing_count,
            delta="Informational" if late_filing_count > 0 else "None",
            delta_color="off"
        )

    # Full watch list table
    st.subheader("Alert Details")
    watch_df = data['watch_list'].copy()

    if len(watch_df) > 0:
        # Calculate filing lag in days
        watch_df['filing_lag_days'] = (
            pd.to_datetime(watch_df['date_learned']) - pd.to_datetime(watch_df['date_happened'])
        ).dt.days

        # Format display columns
        display_df = watch_df[[
            'filer_name', 'alert_type', 'date_happened', 'date_learned',
            'filing_lag_days', 'previous_percent', 'current_percent'
        ]].copy()

        display_df.columns = [
            'Filer Name', 'Alert Type', 'Event Date', 'Filing Date',
            'Lag (days)', 'Previous %', 'Current %'
        ]

        # Apply styling - create a helper that returns correct number of columns
        def style_watch_row(row):
            """Style row based on alert type (returns 7 color values for 7 columns)."""
            alert_type = row['Alert Type']
            # Use light tint backgrounds
            if '13D' in alert_type:
                bg_color = '#FFCDD2'  # Light red
            elif '10%' in alert_type:
                bg_color = '#FFE0B2'  # Light orange
            elif '5%' in alert_type:
                bg_color = '#FFF9C4'  # Light yellow
            else:
                return [''] * len(row)

            return [f'background-color: {bg_color}'] * len(row)

        def style_lag_column(val):
            """Highlight lag column if > 5 days (late filing)."""
            try:
                lag = int(val)
                if lag > 5:
                    return 'font-weight: bold'
            except (ValueError, TypeError):
                pass
            return ''

        # Apply both row and column styling
        styled_watch = display_df.style.apply(style_watch_row, axis=1)
        styled_watch = styled_watch.applymap(style_lag_column, subset=['Lag (days)'])

        st.dataframe(styled_watch, width="stretch", height=400)

        # Download button for watch list
        csv_watch = watch_df.to_csv(index=False)
        st.download_button(
            label="📥 Download Watch List CSV",
            data=csv_watch,
            file_name=f"northwind_watchlist_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            key="download_watchlist"
        )
    else:
        st.info("No threshold crossings or form changes detected in the period.")

    st.markdown('</div>', unsafe_allow_html=True)  # Close alert section box

    # ===========================================
    # SECTION 3: WEEKLY PULSE (Priority 2)
    # ===========================================
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("---")
    st.header("📈 Weekly Activity Pulse (Aug 24-28, 2026)")
    st.caption("Share movements during last trading week")

    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.subheader("Summary by Holder Type")
        weekly_df = data['weekly_activity'].copy()

        if len(weekly_df) > 0:
            # Calculate total metrics
            total_bought = weekly_df['shares_bought'].sum()
            total_sold = weekly_df['shares_sold'].sum()
            net_change = total_bought - total_sold

            # Display metrics
            metric_col1, metric_col2, metric_col3 = st.columns(3)
            metric_col1.metric("Total Bought", format_shares_abbreviated(total_bought))
            metric_col2.metric("Total Sold", format_shares_abbreviated(total_sold))
            metric_col3.metric(
                "Net Change",
                format_shares_abbreviated(abs(net_change)),
                delta=format_delta(net_change, show_sign=False)
            )

            # Format table
            display_weekly = weekly_df.copy()
            display_weekly['shares_bought'] = display_weekly['shares_bought'].apply(format_shares)
            display_weekly['shares_sold'] = display_weekly['shares_sold'].apply(format_shares)
            display_weekly['net_change'] = display_weekly['net_change'].apply(
                lambda x: format_delta(x)
            )
            display_weekly.columns = ['Holder Type', 'Bought', 'Sold', 'Net Change']

            st.dataframe(display_weekly, width="stretch", hide_index=True)
        else:
            st.info("No trading activity detected during the week.")

    with col_right:
        st.subheader("Top 5 Most Active Holders")
        movers_df = data['top_movers'].copy()

        if len(movers_df) > 0:
            # Format for display
            display_movers = movers_df[[
                'holder_name', 'holder_type', 'shares_bought',
                'shares_sold', 'net_change', 'activity_type'
            ]].copy()

            display_movers['shares_bought'] = display_movers['shares_bought'].apply(format_shares)
            display_movers['shares_sold'] = display_movers['shares_sold'].apply(format_shares)
            display_movers['net_change'] = display_movers['net_change'].apply(
                lambda x: format_delta(x)
            )

            display_movers.columns = [
                'Holder Name', 'Type', 'Bought', 'Sold', 'Net Change', 'Activity'
            ]

            # Display without colors - reserve colors for actionable alerts only
            st.dataframe(display_movers, width="stretch", hide_index=True)

            # Download button
            csv_movers = movers_df.to_csv(index=False)
            st.download_button(
                label="📥 Download Weekly Activity Detail CSV",
                data=csv_movers,
                file_name=f"northwind_weekly_activity_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                key="download_activity"
            )
        else:
            st.info("No individual holder activity to display.")

    # ================================
    # SECTION 4: TOP HOLDINGS (Priority 3)
    # ================================
    st.markdown("---")
    st.header("🏆 Top 10 Shareholders")
    st.caption("Ownership as of August 31, 2026 (register + SEC reconciled)")

    holders_df = data['top_holders'].copy()

    if len(holders_df) > 0:
        # Calculate total shares for percentage calculation
        total_outstanding = 39882500  # From shares_outstanding for Aug 3, 2026

        # Prepare display dataframe
        display_holders = pd.DataFrame()
        display_holders['Rank'] = range(1, len(holders_df) + 1)
        display_holders['Holder Name'] = holders_df['holder_name'].values
        display_holders['Type'] = holders_df['holder_type'].values
        display_holders['Register Shares'] = holders_df['register_shares'].apply(format_shares)
        display_holders['SEC Shares'] = holders_df['sec_shares'].apply(
            lambda x: format_shares(x) if pd.notna(x) and x > 0 else "—"
        )
        display_holders['Best Estimate'] = holders_df['best_estimate'].apply(format_shares)
        display_holders['% of Company'] = holders_df['best_estimate'].apply(
            lambda x: format_percent((x / total_outstanding) * 100) if x > 0 else "—"
        )

        # Add reconciliation status
        display_holders['Status'] = holders_df.apply(
            lambda row: format_reconciliation_status(
                row['register_shares'],
                row['sec_shares'] if pd.notna(row['sec_shares']) else None
            ),
            axis=1
        )

        st.dataframe(display_holders, width="stretch", hide_index=True)

        # Key insights
        st.caption(f"""
        **Reconciliation Note:** When a holder appears in both the register and SEC filings,
        we use the HIGHER number (not the sum) to avoid double-counting shares.
        The SEC filing already includes direct register holdings plus indirect holdings via CEDE & CO.
        """)
    else:
        st.info("No holder data available.")

    # ==========================================
    # SECTION 4.5: CRITICAL LIMITATIONS (Visible)
    # ==========================================
    st.markdown("---")
    st.header("⚠️ Important Data Limitations")

    st.warning("""
    **What this dashboard CANNOT show:**

    - **~33 million shares held via CEDE & CO broker nominee** - We can only see beneficial owners behind CEDE if they own 5%+ and file with SEC
    - **Transactions between beneficial owners within CEDE** - These movements are invisible to us
    - **Holdings below 5%** - No SEC filing requirement, so not tracked
    """)

    st.error("""
    **⚠️ Data Quality Alert: Retroactive Changes**

    Register positions may change when late corrections arrive. If you see historical reversals,
    it means we learned about an error AFTER initially recording a transaction.

    **CFO Action Required:** Always re-generate reports on the day of board presentation to ensure latest corrections are included.
    """)

    # ================================
    # SECTION 5: DOWNLOADS
    # ================================
    st.markdown("---")
    st.header("📥 Downloads")
    st.caption("Export data for board packages and further analysis")

    col_pdf, col_info = st.columns([1, 2])

    with col_pdf:
        # Generate and offer PDF download
        try:
            pdf_bytes = generate_executive_pdf(
                data['watch_list'],
                data['weekly_activity'],
                data['top_holders'],
                data['alert_summary']
            )
            st.download_button(
                label="📄 Download Executive Summary PDF",
                data=pdf_bytes,
                file_name=f"northwind_executive_summary_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
                key="download_pdf",
                help="One-page board report with alerts, weekly activity, and top holders"
            )
        except Exception as e:
            st.error(f"PDF generation error: {str(e)}")
            st.caption("Note: Ensure reportlab is installed: `pip install reportlab`")

    with col_info:
        st.info("""
        **Available Downloads:**
        - **Watch List CSV** (in Alerts section): All threshold crossings and form changes
        - **Weekly Activity CSV** (in Activity section): Transaction-level detail for Aug 24-28
        - **Executive Summary PDF** (above): One-page board report ready to present
        """)

    # ================================
    # SECTION 6: DATA QUALITY STATUS
    # ================================
    st.markdown("---")
    st.header("✅ Data Quality Status")

    shares_out_df = data['shares_outstanding']
    if len(shares_out_df) > 0:
        latest = shares_out_df.iloc[-1]  # Most recent reconciliation
        if latest['difference'] == 0:
            st.success(f"""
            **Register Integrity: VALIDATED** ✓

            As of {latest['as_of_date']}, the share register reconciles perfectly with
            company-reported shares outstanding ({format_shares(int(latest['reported_outstanding']))}).

            Register total = {format_shares(int(latest['register_total']))} shares
            (Opening: {format_shares(int(latest['opening_total_may_31']))}
            + Equity issued: {format_shares(int(latest['equity_issued']))}
            - Buybacks: {format_shares(int(latest['shares_repurchased']))})
            """)
        else:
            st.warning(f"""
            **Register Discrepancy Detected** ⚠️

            Difference of {format_shares(abs(int(latest['difference'])))} shares found.
            {latest['explanation']}
            """)

    # ======================================
    # SECTION 7: ADDITIONAL DETAILS (Footer)
    # ======================================
    with st.expander("ℹ️ Additional Technical Details"):
        st.markdown("""
        ### What we CAN see:
        - ✅ **All registered shareholders** on Northwind's official share register
        - ✅ **Large owners (5%+ holders)** who file SC 13D/13G with the SEC
        - ✅ **Every share movement** between registered holders since June 1, 2026

        ### Additional limitations:
        - ❌ **Ownership changes not yet filed** with the SEC (filings can arrive days or weeks after transactions)
        - ❌ **Register transactions not yet recorded** (some recorded days after they happen)
        - ❌ **Synthetic positions** (derivatives, swaps, economic exposure)

        ### Data freshness:
        - **Register events:** Updated throughout the trading day
        - **SEC filings:** Imported once daily (overnight batch from EDGAR)
        - **This dashboard:** Shows data as of August 31, 2026, 4:00 PM ET
        """)

    # Footer
    st.markdown("---")
    st.caption("""
    **Northwind Metals Corp Ownership Intelligence** | Transfer Agent: Shareholder Intelligence Platform
    | For questions, contact: shareholderservices@northwind.example.com
    """)


if __name__ == "__main__":
    main()
