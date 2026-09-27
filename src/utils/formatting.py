"""
Number formatting utilities for Northwind Monday screen dashboard.

Provides consistent formatting for:
- Share counts (with comma separators)
- Percentages (two decimal places)
- Large numbers (abbreviated with M/K suffixes)
- Dates (consistent display format)
"""

from typing import Union, Optional

def format_shares(shares: Union[int, float, None]) -> str:
    """
    Format share count with comma separators.

    Args:
        shares: Number of shares

    Returns:
        Formatted string (e.g., "4,567,890")

    Examples:
        >>> format_shares(4567890)
        '4,567,890'
        >>> format_shares(0)
        '0'
    """
    if shares is None:
        return "—"
    return f"{int(shares):,}"


def format_percent(percent: float, decimals: int = 2) -> str:
    """
    Format percentage with specified decimal places.

    Args:
        percent: Percentage value
        decimals: Number of decimal places (default: 2)

    Returns:
        Formatted string (e.g., "5.15%")

    Examples:
        >>> format_percent(5.15123)
        '5.15%'
        >>> format_percent(10.5, decimals=1)
        '10.5%'
    """
    if percent is None:
        return "—"
    return f"{percent:.{decimals}f}%"


def format_shares_abbreviated(shares: Union[int, float, None]) -> str:
    """
    Format share count with M/K abbreviations for large numbers.

    Args:
        shares: Number of shares

    Returns:
        Abbreviated string (e.g., "2.5M", "350K")

    Examples:
        >>> format_shares_abbreviated(2500000)
        '2.5M'
        >>> format_shares_abbreviated(350000)
        '350K'
        >>> format_shares_abbreviated(1500)
        '1,500'
    """
    if shares is None:
        return "—"

    shares = int(shares)

    if abs(shares) >= 1_000_000:
        return f"{shares / 1_000_000:.1f}M"
    elif abs(shares) >= 1_000:
        return f"{shares / 1_000:.0f}K"
    else:
        return format_shares(shares)


def format_date(date_str: str) -> str:
    """
    Format date string in consistent display format.

    Args:
        date_str: Date string in YYYY-MM-DD format

    Returns:
        Formatted date (e.g., "Aug 31, 2026")

    Examples:
        >>> format_date("2026-08-31")
        'Aug 31, 2026'
    """
    if not date_str:
        return "—"

    from datetime import datetime
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        return date_obj.strftime("%b %d, %Y")
    except:
        return date_str  # Return as-is if parsing fails


def format_currency(amount: float, decimals: int = 0) -> str:
    """
    Format currency amount with dollar sign and comma separators.

    Args:
        amount: Dollar amount
        decimals: Number of decimal places (default: 0)

    Returns:
        Formatted string (e.g., "$1,234,567")

    Examples:
        >>> format_currency(1234567)
        '$1,234,567'
        >>> format_currency(1234.56, decimals=2)
        '$1,234.56'
    """
    if amount is None:
        return "—"
    return f"${amount:,.{decimals}f}"


def format_delta(value: Union[int, float, None], show_sign: bool = True) -> str:
    """
    Format delta/change value with optional +/- sign.

    Args:
        value: Change value
        show_sign: Whether to show + sign for positive values (default: True)

    Returns:
        Formatted string (e.g., "+1,234,567" or "-500,000")

    Examples:
        >>> format_delta(1234567)
        '+1,234,567'
        >>> format_delta(-500000)
        '-500,000'
        >>> format_delta(1234567, show_sign=False)
        '1,234,567'
    """
    if value is None:
        return "—"

    formatted = format_shares(abs(value))

    if value > 0 and show_sign:
        return f"+{formatted}"
    elif value < 0:
        return f"-{formatted}"
    else:
        return formatted


def format_reconciliation_status(register_shares: int, sec_shares: int) -> str:
    """
    Format reconciliation status indicator.

    Args:
        register_shares: Shares on register
        sec_shares: Shares in SEC filing

    Returns:
        Status string ("✓ Match", "⚠️ Mismatch", etc.)

    Examples:
        >>> format_reconciliation_status(1000000, 1000000)
        '✓ Match'
        >>> format_reconciliation_status(1000000, 1500000)
        '⚠️ SEC > Register'
    """
    if register_shares is None or sec_shares is None:
        if register_shares is None and sec_shares is not None:
            return "SEC only"
        elif register_shares is not None and sec_shares is None:
            return "Register only"
        else:
            return "—"

    diff = abs(register_shares - sec_shares)

    if diff < 1:  # Essentially equal (tolerance for rounding)
        return "✓ Match"
    elif sec_shares > register_shares:
        return "⚠️ SEC > Register"
    else:
        return "⚠️ Register > SEC"
