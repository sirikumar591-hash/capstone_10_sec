"""
Tests for BR-09: Long-stay and Auction Rules.
"""
from datetime import datetime
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
        TariffItem(ChargeCode.AUCTION_PROCESSING.value, Decimal("10000.00"), "per container"),
        TariffItem(ChargeCode.DELISTING.value, Decimal("2000.00"), "per container"),
    ]
    return TariffTable(items)


def test_BR09_auction_listing_after_30_days(sample_tariff):
    holidays = set()
    free_days = FreeDaysService(holidays, {("IMPORT", "DRY"): 3})
    dem_service = DemurrageService(sample_tariff, free_days)

    c = Container("C01", 20, ContainerType.DRY, Decimal("10.00"), Direction.IMPORT, "VSL-01", "KVL", "ICD", "PTY-01")
    c.discharge_ts = datetime(2026, 8, 1, 10, 0, 0)

    # 31 days in yard (Sept 1)
    res = dem_service.calculate_demurrage(c, datetime(2026, 9, 1, 12, 0, 0))
    assert res.is_auction_listed is True


def test_BR09_long_stay_demurrage_cap_from_day_45(sample_tariff):
    holidays = set()
    free_days = FreeDaysService(holidays, {("IMPORT", "DRY"): 3})
    dem_service = DemurrageService(sample_tariff, free_days)

    c = Container("C01", 20, ContainerType.DRY, Decimal("10.00"), Direction.IMPORT, "VSL-01", "KVL", "ICD", "PTY-01")
    c.discharge_ts = datetime(2026, 8, 1, 10, 0, 0)

    # 60 days in yard (Sept 30) -> Cap = 3500 * 45 = 157,500.00 + 10,000 auction fee
    res = dem_service.calculate_demurrage(c, datetime(2026, 9, 30, 12, 0, 0))
    assert res.is_capped is True
    assert res.capped_demurrage == Decimal("157500.00")
    assert res.auction_fee == Decimal("10000.00")

