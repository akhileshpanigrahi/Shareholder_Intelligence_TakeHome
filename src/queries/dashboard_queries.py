"""
Query execution wrapper functions for Northwind Monday screen dashboard.

Provides Python functions that execute SQL queries and return pandas DataFrames.
All queries are read from SQL files to maintain separation of concerns.
"""

import sqlite3
import pandas as pd
from pathlib import Path


class DashboardQueries:
    """
    Wrapper class for executing dashboard SQL queries.

    Attributes:
        conn: SQLite database connection
        queries_dir: Path to queries directory
    """

    def __init__(self, db_path: str = "northwind.db"):
        """
        Initialize query executor with database connection.

        Args:
            db_path: Path to SQLite database file
        """
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.queries_dir = Path("queries")

    def _execute_query(self, sql_file: str) -> pd.DataFrame:
        """
        Execute SQL query from file and return DataFrame.

        Args:
            sql_file: Name of SQL file in queries directory

        Returns:
            pandas DataFrame with query results
        """
        sql_path = self.queries_dir / sql_file
        with open(sql_path, 'r') as f:
            sql = f.read()
        return pd.read_sql_query(sql, self.conn)

    def get_watch_list(self) -> pd.DataFrame:
        """
        Get all watch list alerts (Query 4).

        Returns threshold crossings and 13G→13D conversions from June 1 - August 31, 2026.

        Returns:
            DataFrame with columns:
            - filer_cik, filer_name
            - date_happened (event_date), date_learned (filing_date)
            - alert_type (e.g., "Changed from 13G to 13D", "Crossed above 5%")
            - previous_percent, current_percent
            - previous_form, current_form
        """
        return self._execute_query("query4_watch_list.sql")

    def get_weekly_activity(self) -> pd.DataFrame:
        """
        Get weekly buy/sell activity by holder type (Query 2).

        Aggregates share movements for August 24-28, 2026 by holder type.

        Returns:
            DataFrame with columns:
            - holder_type (institution, individual, insider, etc.)
            - shares_bought, shares_sold, net_change
        """
        return self._execute_query("query2_weekly_activity.sql")

    def get_top_holders(self) -> pd.DataFrame:
        """
        Get top 10 shareholders (Query 1).

        Shows ownership as of August 31, 2026 from both register and SEC sources.

        Returns:
            DataFrame with columns:
            - holder_id, holder_name, holder_type, filer_cik
            - register_shares, sec_shares, best_estimate
        """
        return self._execute_query("query1_top_holders.sql")

    def get_top_movers(self) -> pd.DataFrame:
        """
        Get top 5 weekly movers (NEW dashboard query).

        Identifies individual holders with largest absolute net share change
        during August 24-28, 2026.

        Returns:
            DataFrame with columns:
            - holder_id, holder_name, holder_type
            - shares_bought, shares_sold, net_change
            - activity_type ('buyer', 'seller', 'neutral')
        """
        return self._execute_query("dashboard_top_movers.sql")

    def get_alert_summary(self) -> dict:
        """
        Get alert count summary for badge display.

        Calculates counts of each alert type from watch list.

        Returns:
            dict with keys:
            - activist_alerts: Count of 13G→13D conversions
            - threshold_10_alerts: Count of 10% crossings
            - threshold_5_alerts: Count of 5% crossings
            - late_filing_alerts: Count of filings with lag > 5 days
        """
        watch_list = self.get_watch_list()

        # Calculate filing lag for late filing detection
        watch_list['filing_lag_days'] = (
            pd.to_datetime(watch_list['date_learned']) - pd.to_datetime(watch_list['date_happened'])
        ).dt.days

        return {
            'activist_alerts': len(watch_list[watch_list['alert_type'] == 'Changed from 13G to 13D']),
            'threshold_10_alerts': len(watch_list[watch_list['alert_type'].str.contains('10%', na=False)]),
            'threshold_5_alerts': len(watch_list[watch_list['alert_type'].str.contains('5%', na=False)]),
            'late_filing_alerts': len(watch_list[watch_list['filing_lag_days'] > 5])
        }

    def get_shares_outstanding_validation(self) -> pd.DataFrame:
        """
        Get shares outstanding reconciliation (Query 6).

        Validates register total against company-reported shares outstanding.

        Returns:
            DataFrame with columns:
            - as_of_date
            - opening_total_may_31, equity_issued, shares_repurchased
            - register_total, reported_outstanding, difference
            - explanation, filing_source, date_published
        """
        return self._execute_query("query6_shares_outstanding.sql")

    def close(self):
        """Close database connection."""
        self.conn.close()
