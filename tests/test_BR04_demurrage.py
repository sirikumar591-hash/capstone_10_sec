"""
Tests for BR-04: Demurrage Slabs, Multipliers, and Partial Days.
"""
from datetime import date, datetime
from decimal import Decimal
import pytest
from src.models.container import Container
from src.models.tariff import TariffItem, TariffTable
from src.services.demurrage_service import DemurrageService
from src.services.free_days_service import FreeDaysService
from src.utils.constants import ChargeCode, ContainerType, Direction


@pytest.fixture
def sample_tariff():
    items = [
        TariffItem(ChargeCode.DEMURRAGE_DRY.value, Decimal("1200.00"), "per day", 20, 1, 5),
        TariffItem(ChargeCode.DEMURRAGE_DRY.value, Decimal("2000.00"), "per day", 20, 6, 10),
        TariffItem(ChargeCode.DEMURRAGE_DRY.value, Decimal("3500.00"), "per day", 20, 11, None),
        TariffItem(ChargeCode.SIZE_MULT_40.value, Decimal("1.60"), "multiplier", 40),
        TariffItem(ChargeCode.TYPE_MULT_REEFER.value, Decimal("2.00"), "multiplier"),
        TariffItem(ChargeCode.TYPE_MULT_HAZ.value, Decimal("1.50"), "multiplier"),
        TariffItem(ChargeCode.OVERFLOW_STORAGE_MULT.value, Decimal("1.50"), "multiplier"),
        TariffItem(ChargeCode.AUCTION_PROCESSING.value, Decimal("10000.00"), "per container"),
        TariffItem(ChargeCode.DELISTING.value, Decimal("2000.00"), "per container"),
    ]
    return TariffTable(items)


def test_BR04_20ft_dry_slabs(sample_tariff):
    """Verify 20-ft DRY base demurrage across slabs."""
    holidays = set()
    free_days = FreeDaysService(holidays, {("IMPORT", "DRY"): 3})
    dem_service = DemurrageService(sample_tariff, free_days)

    c = Container("C20", 20, ContainerType.DRY, Decimal("15.00"), Direction.IMPORT, "VSL-01", "KVL", "ICD", "PTY-01")
    c.discharge_ts = datetime(2026, 8, 1, 10, 0, 0)
    # Free days: Aug 1 + 3 days = Aug 4. Demurrage starts Aug 5.

    # Evaluated on Aug 6 (Day 2 of demurrage -> 2 days @ 1200 = 2400)
    res = dem_service.calculate_demurrage(c, datetime(2026, 8, 6, 15, 0, 0))
    assert res.net_chargeable_days == 2
    assert res.capped_demurrage == Decimal("2400.00")


def test_BR04_40ft_multiplier(sample_tariff):
    """Verify 40-ft container receives 1.6x multiplier."""
    holidays = set()
    free_days = FreeDaysService(holidays, {("IMPORT", "DRY"): 3})
    dem_service = DemurrageService(sample_tariff, free_days)

    c = Container("C40", 40, ContainerType.DRY, Decimal("20.00"), Direction.IMPORT, "VSL-01", "KVL", "ICD", "PTY-01")
    c.discharge_ts = datetime(2026, 8, 1, 10, 0, 0)
    # Last free day Aug 4. Demurrage starts Aug 5.
    # Day 1 demurrage = 1200 * 1.6 = 1920.00
    res = dem_service.calculate_demurrage(c, datetime(2026, 8, 5, 12, 0, 0))
    assert res.net_chargeable_days == 1
    assert res.capped_demurrage == Decimal("1920.00")


def test_BR04_partial_day_counts_as_full_day(sample_tariff):
    """A partial chargeable day counts as a complete day."""
    holidays = set()
    free_days = FreeDaysService(holidays, {("IMPORT", "DRY"): 3})
    dem_service = DemurrageService(sample_tariff, free_days)

    c = Container("C40", 40, ContainerType.DRY, Decimal("20.00"), Direction.IMPORT, "VSL-02", "DSL", "ICD", "PTY-01")
    c.discharge_ts = datetime(2026, 8, 14, 10, 0, 0)
    # Free days: Aug 14 + 3 = Aug 17. Demurrage starts Aug 18.
    # Gated out on Aug 23 at 00:05 (5 minutes into Day 6)
    # Chargeable days = 6 days (5 days slab 1 @ 1920 + 1 day slab 2 @ 2000*1.6 = 3200)
    # Total = (5 * 1920) + 3200 = 9600 + 3200 = 12800.00
    res = dem_service.calculate_demurrage(c, datetime(2026, 8, 23, 0, 5, 0))
    assert res.net_chargeable_days == 6
    assert res.capped_demurrage == Decimal("12800.00")

