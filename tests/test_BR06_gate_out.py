"""
Tests for BR-06: Gate-out Hold Checks and Customs Exam Waivers.
"""
from datetime import datetime
from decimal import Decimal
import pytest
from src.models.container import Container
from src.services.gate_service import GateService
from src.utils.constants import ContainerType, Direction


def test_BR06_gate_out_holds():
    """Gate out rejected if OOC, Delivery Order, or Payment Receipt is missing."""
    c = Container("C01", 20, ContainerType.DRY, Decimal("10.00"), Direction.IMPORT, "VSL-01", "KVL", "ICD", "PTY-01")
    ts = datetime(2026, 8, 10, 12, 0, 0)

    # 1. Missing payment receipt
    valid, err = GateService.validate_gate_out(c, ts, customs_ooc="true", delivery_order="true", payment_receipt="-")
    assert valid is False
    assert "paid in full" in err

    # 2. Missing OOC
    valid, err = GateService.validate_gate_out(c, ts, customs_ooc="false", delivery_order="true", payment_receipt="RCP-123")
    assert valid is False
    assert "Out of Charge" in err

    # 3. Missing Delivery Order
    valid, err = GateService.validate_gate_out(c, ts, customs_ooc="true", delivery_order="false", payment_receipt="RCP-123")
    assert valid is False
    assert "Delivery Order" in err

    # 4. Under active customs exam
    c.exam_start_ts = datetime(2026, 8, 10, 8, 0, 0)
    valid, err = GateService.validate_gate_out(c, ts, customs_ooc="true", delivery_order="true", payment_receipt="RCP-123")
    assert valid is False
    assert "customs examination" in err

    # 5. All valid
    c.exam_end_ts = datetime(2026, 8, 10, 11, 0, 0)
    valid, err = GateService.validate_gate_out(c, ts, customs_ooc="true", delivery_order="true", payment_receipt="RCP-123")
    assert valid is True
    assert err is None

