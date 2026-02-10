"""
Shared money parsing utilities with multi-locale support.

Handles various number formats:
- US: 1,234.56
- European: 1.234,56 or 1 234.56
- Negative: -$12.34 or ($12.34)
- Missing decimals: 1234 → 1234.00
"""

from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Optional
import re


class MoneyFormat(Enum):
    """Money format locale hints."""
    US = "US"  # 1,234.56
    EUROPEAN = "EUROPEAN"  # 1.234,56 or 1 234.56
    AUTO = "AUTO"  # Auto-detect based on patterns


def parse_money(
    amount_str: str,
    format_hint: Optional[MoneyFormat] = None,
    allow_negative: bool = False
) -> Optional[Decimal]:
    """
    Parse money string with multi-locale support.

    Args:
        amount_str: String containing amount (e.g., "$1,234.56", "1.234,56 EUR")
        format_hint: Optional locale hint (US, EUROPEAN, AUTO)
        allow_negative: Whether to allow negative amounts

    Returns:
        Decimal amount or None if parsing fails

    Examples:
        >>> parse_money("$1,234.56")
        Decimal('1234.56')
        >>> parse_money("1.234,56", format_hint=MoneyFormat.EUROPEAN)
        Decimal('1234.56')
        >>> parse_money("($12.34)", allow_negative=True)
        Decimal('-12.34')
    """
    if not amount_str or not isinstance(amount_str, str):
        return None

    # Detect if negative (parentheses or minus sign)
    is_negative = False
    cleaned = amount_str.strip()

    # Handle parentheses notation for negative amounts
    if cleaned.startswith('(') and cleaned.endswith(')'):
        if not allow_negative:
            return None
        is_negative = True
        cleaned = cleaned[1:-1].strip()

    # Handle minus sign
    if cleaned.startswith('-'):
        if not allow_negative:
            return None
        is_negative = True
        cleaned = cleaned[1:].strip()

    # Strip currency symbols and common prefixes
    # Remove: $, £, €, ¥, USD, CAD, EUR, GBP, etc.
    currency_pattern = r'[$£€¥]\s*|[A-Z]{3}\s*'
    cleaned = re.sub(currency_pattern, '', cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.strip()

    if not cleaned:
        return None

    # Determine format
    detected_format = format_hint or MoneyFormat.AUTO

    if detected_format == MoneyFormat.AUTO:
        detected_format = _detect_money_format(cleaned)

    # Parse based on format
    try:
        if detected_format == MoneyFormat.EUROPEAN:
            result = _parse_european_format(cleaned)
        else:  # US or fallback
            result = _parse_us_format(cleaned)

        if result is None:
            return None

        # Apply negative sign if needed
        if is_negative:
            result = -result

        # Sanity check: amount should be reasonable (< $1 million for receipts)
        if abs(result) > 1_000_000:
            return None

        return result

    except (InvalidOperation, ValueError, AttributeError):
        return None


def _detect_money_format(amount_str: str) -> MoneyFormat:
    """
    Auto-detect money format based on separator patterns.

    Heuristics:
    - If ends with ,XX (comma + 2 digits), assume European
    - If contains space as thousands separator, assume European
    - Otherwise assume US
    """
    # European: ends with comma and 2 digits (e.g., "1.234,56")
    if re.search(r',\d{2}$', amount_str):
        return MoneyFormat.EUROPEAN

    # European: uses space as thousands separator (e.g., "1 234.56")
    if ' ' in amount_str and '.' not in amount_str:
        return MoneyFormat.EUROPEAN

    # European: dot used as thousands, comma as decimal
    if '.' in amount_str and ',' in amount_str:
        # If dot comes before comma, European format
        if amount_str.index('.') < amount_str.rindex(','):
            return MoneyFormat.EUROPEAN

    # Default to US
    return MoneyFormat.US


def _parse_us_format(amount_str: str) -> Optional[Decimal]:
    """
    Parse US format: 1,234.56

    - Comma as thousands separator
    - Dot as decimal separator
    """
    # Remove commas (thousands separator)
    cleaned = amount_str.replace(',', '')

    # Remove spaces
    cleaned = cleaned.replace(' ', '')

    # Parse as decimal
    try:
        return Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return None


def _parse_european_format(amount_str: str) -> Optional[Decimal]:
    """
    Parse European format: 1.234,56 or 1 234,56

    - Dot or space as thousands separator
    - Comma as decimal separator
    """
    # Remove dots and spaces (thousands separators)
    cleaned = amount_str.replace('.', '').replace(' ', '')

    # Replace comma with dot (decimal separator)
    cleaned = cleaned.replace(',', '.')

    # Parse as decimal
    try:
        return Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return None


def format_money(amount: Decimal, currency: str = 'USD') -> str:
    """
    Format Decimal amount as money string.

    Args:
        amount: Decimal amount
        currency: Currency code (default: USD)

    Returns:
        Formatted string (e.g., "$1,234.56")

    Examples:
        >>> format_money(Decimal('1234.56'))
        '$1,234.56'
        >>> format_money(Decimal('1234.56'), 'EUR')
        '€1,234.56'
    """
    if amount is None:
        return 'N/A'

    # Get currency symbol
    symbol_map = {
        'USD': '$',
        'CAD': '$',
        'EUR': '€',
        'GBP': '£',
        'JPY': '¥',
        'AUD': '$',
    }
    symbol = symbol_map.get(currency.upper(), currency)

    # Format with thousands separator
    # Convert to float for formatting, then back to string
    amount_float = float(amount)
    formatted = f"{amount_float:,.2f}"

    return f"{symbol}{formatted}"
