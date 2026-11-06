"""
Money Utilities for Financial Calculations using Python Decimal.
Ensures zero floating-point inaccuracy in billing.
"""
from decimal import Decimal, ROUND_HALF_UP
from typing import Union

TWOPLACES = Decimal("0.01")


def to_decimal(value: Union[int, float, str, Decimal, None]) -> Decimal:
    """Converts a value to Decimal safely."""
    if value is None or value == "" or value == "-":
        return Decimal("0.00")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def round_money(amount: Union[int, float, str, Decimal]) -> Decimal:
    """Rounds amount to 2 decimal places using standard ROUND_HALF_UP."""
    d = to_decimal(amount)
    return d.quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def format_money(amount: Union[int, float, str, Decimal, None]) -> str:
    """Formats amount as plain decimal string with 2 decimal places, e.g. 1200.00."""
    if amount is None or amount == "" or amount == "-":
        return ""
    d = round_money(amount)
    return f"{d:.2f}"
