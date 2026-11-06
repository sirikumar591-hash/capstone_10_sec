"""
Tests for BR-08: Shut-Out Rules.
"""
from datetime import datetime
from decimal import Decimal
import pytest
from src.models.container import Container
from src.models.tariff import TariffItem, TariffTable
from src.services.operations_service import OperationsService
from src.utils.constants import ChargeCode, ContainerType, Direction, ShutOutReason


@pytest.fixture
def sample_tariff():
    items = [
        TariffItem(ChargeCode.SHUT_OUT.value, Decimal("5000.00"), "per container"),
    ]
    return TariffTable(items)


def test_BR08_shut_out_line_cutoff_vs_yard_congestion(sample_tariff):
    service = OperationsService(sample_tariff)
    c1 = Container("C01", 20, ContainerType.DRY, Decimal("10.00"), Direction.EXPORT, "VSL-02", "DSL", "ICD", "PTY-01")
    ts = datetime(2026, 8, 13, 11, 0, 0)

    # Line cut-off -> Rs 5,000 fee
    fee, reason = service.process_shut_out(c1, ts, ShutOutReason.LINE_CUTOFF.value)
    assert fee == Decimal("5000.00")
    assert reason == ShutOutReason.LINE_CUTOFF

    # Yard congestion -> Rs 0 fee
    c2 = Container("C02", 20, ContainerType.DRY, Decimal("10.00"), Direction.EXPORT, "VSL-02", "DSL", "ICD", "PTY-01")
    fee, reason = service.process_shut_out(c2, ts, ShutOutReason.YARD_CONGESTION.value)
    assert fee == Decimal("0.00")
    assert reason == ShutOutReason.YARD_CONGESTION

