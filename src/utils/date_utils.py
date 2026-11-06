"""
Date and Timestamp Utilities for Logistics Calculations.
Strict adherence to IST timestamps: YYYY-MM-DD HH:MM:SS and dates: YYYY-MM-DD.
"""
from datetime import datetime, date, timedelta
from typing import Set, Union

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"


def parse_datetime(ts_str: str) -> datetime:
    """Parses timestamp string YYYY-MM-DD HH:MM:SS."""
    return datetime.strptime(ts_str.strip(), DATETIME_FORMAT)


def parse_date(date_str: str) -> date:
    """Parses date string YYYY-MM-DD."""
    return datetime.strptime(date_str.strip(), DATE_FORMAT).date()


def format_datetime(dt: datetime) -> str:
    """Formats datetime to YYYY-MM-DD HH:MM:SS."""
    return dt.strftime(DATETIME_FORMAT)


def format_date(d: Union[date, datetime]) -> str:
    """Formats date or datetime to YYYY-MM-DD."""
    if isinstance(d, datetime):
        return d.strftime(DATE_FORMAT)
    return d.strftime(DATE_FORMAT)


def is_non_working_day(d: date, holidays: Set[date]) -> bool:
    """
    Checks if a date is a non-working day.
    Sundays (weekday == 6) and official terminal holidays are non-working days.
    """
    return d.weekday() == 6 or d in holidays


def calculate_last_free_day(start_date: date, free_days_count: int, holidays: Set[date]) -> date:
    """
    Calculates the last free day for import containers.
    A free period of N days counted from start_date ends on (start_date + N).
    If that day falls on a Sunday or holiday, it moves iteratively to the next working day.
    """
    end_date = start_date + timedelta(days=free_days_count)
    while is_non_working_day(end_date, holidays):
        end_date += timedelta(days=1)
    return end_date
