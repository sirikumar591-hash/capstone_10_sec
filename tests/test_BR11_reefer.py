"""
Tests for BR-11: Reefer Temperature Deviation and Plug-in Billing.
"""
from datetime import datetime
from decimal import Decimal
import pytest
from src.models.container import Container
from src.models.tariff import TariffItem, TariffTable
from src.services.reefer_service import ReeferService
from src.utils.constants import ChargeCode, ContainerType, Direction, Flag


@pytest.fixture
def sample_tariff():
    items = [
        TariffItem(ChargeCode.REEFER_PLUG.value, Decimal("2500.00"), "per day"),
    ]
    return TariffTable(items)


def test_BR11_exactly_four_hours_deviation_no_claim_risk(sample_tariff):
    """Exactly 4 hours must NOT create CLAIM_RISK and must not pause billing."""
    service = ReeferService(sample_tariff)
    c = Container("RF01", 20, ContainerType.REEFER, Decimal("15.00"), Direction.IMPORT, "VSL-01", "KVL", "ICD", "PTY-01")
    c.discharge_ts = datetime(2026, 8, 1, 10, 0, 0)

    # Exactly 4 hours
    start_ts = datetime(2026, 8, 2, 10, 0, 0)
    end_ts = datetime(2026, 8, 2, 14, 0, 0)
    flagged = service.process_temperature_deviation(c, start_ts, end_ts, Decimal("10.00"))

    assert flagged is False
    assert Flag.CLAIM_RISK.value not in c.flags
    assert len(c.temperature_deviations) == 0


def test_BR11_exceeding_four_hours_deviation_creates_claim_risk_and_pauses_billing(sample_tariff):
    """Deviation exceeding 4 hours creates CLAIM_RISK and pauses plug-in billing."""
    service = ReeferService(sample_tariff)
    c = Container("RF02", 20, ContainerType.REEFER, Decimal("15.00"), Direction.IMPORT, "VSL-01", "KVL", "ICD", "PTY-01")
    c.discharge_ts = datetime(2026, 8, 1, 0, 0, 0)
    c.gate_out_ts = datetime(2026, 8, 2, 0, 0, 0)  # 1 full day (24h) = 2500

    # 5 hours deviation
    start_ts = datetime(2026, 8, 1, 10, 0, 0)
    end_ts = datetime(2026, 8, 1, 15, 0, 0)
    flagged = service.process_temperature_deviation(c, start_ts, end_ts, Decimal("12.00"))

    assert flagged is True
    assert Flag.CLAIM_RISK.value in c.flags
    assert len(c.temperature_deviations) == 1

    # Total charge should be 2500 - (2500/24 * 5) = 2500 - 520.83 = 1979.17
    charge = service.calculate_plugin_charge(c, datetime(2026, 8, 2, 0, 0, 0))
    expected = (Decimal("2500.00") - (Decimal("2500.00") / Decimal("24.00") * Decimal("5.00"))).quantize(Decimal("0.01"))
    assert charge == expected

