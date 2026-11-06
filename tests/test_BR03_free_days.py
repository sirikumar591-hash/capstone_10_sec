"""
Tests for BR-03: Free Days Calculation and Holiday Extensions.
"""
from datetime import date, datetime
import pytest
from src.services.free_days_service import FreeDaysService
from src.utils.constants import ContainerType


def test_BR03_normal_import_free_days():
    """Normal import containers get 3 free calendar days."""
    holidays = set()
    rules = {("IMPORT", "DRY"): 3, ("IMPORT", "REEFER"): 5}
    service = FreeDaysService(holidays, rules)

    # Discharged on Wednesday 2026-08-05
    ts = datetime(2026, 8, 5, 10, 0, 0)
    last_free = service.calculate_import_last_free_day(ts, ContainerType.DRY)
    # 2026-08-05 + 3 days = 2026-08-08 (Saturday, working day)
    assert last_free == date(2026, 8, 8)


def test_BR03_reefer_import_free_days():
    """Import REEFER containers get 5 free calendar days."""
    holidays = set()
    rules = {("IMPORT", "DRY"): 3, ("IMPORT", "REEFER"): 5}
    service = FreeDaysService(holidays, rules)

    # Discharged on Monday 2026-08-03
    ts = datetime(2026, 8, 3, 18, 0, 0)
    last_free = service.calculate_import_last_free_day(ts, ContainerType.REEFER)
    # 2026-08-03 + 5 days = 2026-08-08 (Saturday)
    assert last_free == date(2026, 8, 8)


def test_BR03_sunday_and_holiday_recursive_extension():
    """If last free day falls on Sunday or terminal holiday, extend to next working day."""
    holidays = {date(2026, 9, 14)}  # Monday holiday (Ganesh Chaturthi)
    rules = {("IMPORT", "DRY"): 3}
    service = FreeDaysService(holidays, rules)

    # Discharged on Thursday 2026-09-10
    ts = datetime(2026, 9, 10, 14, 0, 0)
    last_free = service.calculate_import_last_free_day(ts, ContainerType.DRY)
    # 2026-09-10 + 3 days = 2026-09-13 (Sunday) -> next day 2026-09-14 (Holiday) -> next day 2026-09-15 (Tuesday, working day)
    assert last_free == date(2026, 9, 15)

