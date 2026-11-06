"""
Tests for BR-05: Detention Charges.
"""
from datetime import datetime
from decimal import Decimal
import pytest
from src.models.container import Container
from src.models.tariff import TariffItem, TariffTable
from src.services.detention_service import DetentionService
from src.utils.constants import ChargeCode, ContainerType, Direction


@pytest.fixture
def sample_tariff():
    items = [
        TariffItem(ChargeCode.DETENTION.value, Decimal("1500.00"), "per day", 20, 8, 14),
        TariffItem(ChargeCode.DETENTION.value, Decimal("2800.00"), "per day", 40, 8, 14),
    ]
    return TariffTable(items)


def test_BR05_seven_days_free(sample_tariff):
    """Empty return within 7 days of gate-out incurs zero detention."""
    service = DetentionService(sample_tariff)
    c = Container("C40", 40, ContainerType.DRY, Decimal("20.00"), Direction.IMPORT, "VSL-01", "KVL", "ICD", "PTY-01")
    c.gate_out_ts = datetime(2026, 8, 4, 13, 0, 0)
    c.empty_return_ts = datetime(2026, 8, 11, 10, 0, 0)  # 7 days later

    res = service.calculate_detention(c, datetime(2026, 8, 30))
    assert res.chargeable_days == 0
    assert res.detention_amount == Decimal("0.00")


def test_BR05_detention_slabs_and_doubling(sample_tariff):
    """After day 14, daily detention rate doubles."""
    service = DetentionService(sample_tariff)
    c = Container("C20", 20, ContainerType.DRY, Decimal("15.00"), Direction.IMPORT, "VSL-01", "KVL", "ICD", "PTY-01")
    c.gate_out_ts = datetime(2026, 8, 1, 10, 0, 0)
    # Empty return 15 days later (Aug 16)
    # Days 1-7: free
    # Days 8-14: 7 days @ 1500 = 10,500
    # Day 15: 1 day @ double rate (3000) = 3,000
    # Total = 13,500
    c.empty_return_ts = datetime(2026, 8, 16, 10, 0, 0)
    res = service.calculate_detention(c, datetime(2026, 8, 30))
    assert res.chargeable_days == 8
    assert res.detention_amount == Decimal("13500.00")

