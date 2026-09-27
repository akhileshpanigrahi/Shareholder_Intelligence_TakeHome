"""
Color scheme constants for Northwind Monday screen dashboard.

Provides consistent color coding across all visualizations:
- Critical alerts (activist conversions): RED
- Warning alerts (threshold crossings): ORANGE/YELLOW
- Position changes: GREEN (buyers) / RED (sellers)
"""

# Alert severity colors
CRITICAL_RED = "#D32F2F"      # 13G→13D conversions
WARNING_ORANGE = "#F57C00"    # 10% threshold crossings
WARNING_YELLOW = "#FFA000"    # 5% threshold crossings
INFO_BLUE = "#1976D2"         # Informational items

# Position change colors
BUYER_GREEN = "#388E3C"       # Net buyers
SELLER_RED = "#E53935"        # Net sellers
NEUTRAL_GRAY = "#757575"      # No net change

# Success/status colors
SUCCESS_GREEN = "#4CAF50"     # Data quality checks passing
MATCH_GREEN = "#C8E6C9"       # Reconciliation matches (light green background)

# Error/mismatch colors
ERROR_RED = "#F44336"         # Data quality errors
MISMATCH_RED = "#FFCDD2"      # Reconciliation mismatches (light red background)

# Alert background tints (for table row highlighting)
ACTIVIST_ALERT_BG = "#FFCDD2"       # Light red tint
THRESHOLD_10_ALERT_BG = "#FFE0B2"   # Light orange tint
THRESHOLD_5_ALERT_BG = "#FFF9C4"    # Light yellow tint

# Alert color mapping dictionary
ALERT_COLORS = {
    'activist': CRITICAL_RED,
    'threshold_10_up': WARNING_ORANGE,
    'threshold_10_down': WARNING_ORANGE,
    'threshold_5_up': WARNING_YELLOW,
    'threshold_5_down': WARNING_YELLOW,
    'late_filing': INFO_BLUE
}

# Alert background color mapping
ALERT_BACKGROUNDS = {
    'activist': ACTIVIST_ALERT_BG,
    'threshold_10': THRESHOLD_10_ALERT_BG,
    'threshold_5': THRESHOLD_5_ALERT_BG
}

# Position change color mapping
POSITION_COLORS = {
    'buyer': BUYER_GREEN,
    'seller': SELLER_RED,
    'neutral': NEUTRAL_GRAY
}


def get_alert_color(alert_type: str) -> str:
    """
    Get the appropriate color for an alert type.

    Args:
        alert_type: Alert type string (e.g., "Changed from 13G to 13D")

    Returns:
        Hex color code
    """
    if '13D' in alert_type:
        return CRITICAL_RED
    elif '10%' in alert_type:
        return WARNING_ORANGE
    elif '5%' in alert_type:
        return WARNING_YELLOW
    else:
        return INFO_BLUE


def get_alert_background(alert_type: str) -> str:
    """
    Get the appropriate background color for an alert row.

    Args:
        alert_type: Alert type string

    Returns:
        Hex color code for background
    """
    if '13D' in alert_type:
        return ACTIVIST_ALERT_BG
    elif '10%' in alert_type:
        return THRESHOLD_10_ALERT_BG
    elif '5%' in alert_type:
        return THRESHOLD_5_ALERT_BG
    else:
        return None  # No background color


def get_position_color(net_change: float) -> str:
    """
    Get the appropriate color for a position change.

    Args:
        net_change: Net share change (positive = buyer, negative = seller)

    Returns:
        Hex color code
    """
    if net_change > 0:
        return BUYER_GREEN
    elif net_change < 0:
        return SELLER_RED
    else:
        return NEUTRAL_GRAY
