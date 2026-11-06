"""
Tests for BR-07: Lift Charges and Restow Attribution.
"""
from datetime import datetime
from decimal import Decimal
import pytest
from src.models.container import Container
from src.models.tariff import TariffItem, TariffTable
from src.services.operations_service import OperationsService
from src.utils.constants import ChargeCode, ContainerType, Direction, RestowReason


@pytest.fixture
def sample_tariff():
    items = [
        TariffItem(ChargeCode.LIFT.value, Decimal("3000.00"), "per lift", 20),
        TariffItem(ChargeCode.LIFT.value, Decimal("4500.00"), "per lift", 40),
    ]
    return TariffTable(items)


def test_BR07_lift_charges(sample_tariff):
    service = OperationsService(sample_tariff)
    assert service.get_lift_charge(20) == Decimal("3000.00")
    assert service.get_lift_charge(40) == Decimal("4500.00")


def test_BR07_restow_attribution(sample_tariff):
    service = OperationsService(sample_tariff)
    c = Container("C01", 20, ContainerType.DRY, Decimal("10.00"), Direction.IMPORT, "VSL-01", "KVL", "ICD", "PTY-01")
    ts = datetime(2026, 8, 10, 12, 0, 0)

    # Restow for terminal access -> billed to TERMINAL
    fee, bill_to = service.process_restow(c, ts, RestowReason.TERMINAL_ACCESS.value)
    assert fee == Decimal("3000.00")
    assert bill_to == "TERMINAL"

    # Restow for consignee request -> billed to consignee party_id
    fee, bill_to = service.process_restow(c, ts, RestowReason.CONSIGNEE_REQUEST.value)
    assert fee == Decimal("3000.00")
    assert bill_to == "PTY-01"

