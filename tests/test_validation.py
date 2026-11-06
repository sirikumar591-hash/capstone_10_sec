"""
Tests for Step 5: Input Validation and Integrity Constraints.
"""
from datetime import datetime
from decimal import Decimal
import pytest
from src.models.container import Container
from src.models.vessel import Vessel
from src.models.yard_block import YardBlock
from src.utils.constants import ContainerState, ContainerType, Direction
from src.validators.input_validator import InputValidator


@pytest.fixture
def sample_vessels():
    return {
        "VSL-01": Vessel("VSL-01", "MV Kaveri", "042E", "KVL", datetime(2026, 8, 2), datetime(2026, 8, 4), datetime(2026, 8, 3))
    }


def test_validation_invalid_size(sample_vessels):
    """Validation detects invalid container sizes (not 20 or 40)."""
    c = Container("C01", 45, ContainerType.DRY, Decimal("10.00"), Direction.IMPORT, "VSL-01", "KVL", "ICD", "PTY-01")
    errs = InputValidator.validate_container(c, sample_vessels)
    assert any("Invalid size 45" in e for e in errs)


def test_validation_negative_weight(sample_vessels):
    """Validation detects negative gross weights."""
    c = Container("C02", 20, ContainerType.DRY, Decimal("-5.00"), Direction.IMPORT, "VSL-01", "KVL", "ICD", "PTY-01")
    errs = InputValidator.validate_container(c, sample_vessels)
    assert any("Negative gross weight" in e for e in errs)


def test_validation_invalid_imo_class(sample_vessels):
    """HAZ containers must have a recognized IMO class."""
    c = Container("C03", 20, ContainerType.HAZ, Decimal("15.00"), Direction.IMPORT, "VSL-01", "KVL", "ICD", "PTY-01", imo_class="15.0")
    errs = InputValidator.validate_container(c, sample_vessels)
    assert any("invalid IMO class" in e for e in errs)


def test_validation_missing_vessel_reference(sample_vessels):
    """Container with unknown vessel_id must be flagged."""
    c = Container("C04", 20, ContainerType.DRY, Decimal("15.00"), Direction.IMPORT, "UNKNOWN_VSL", "KVL", "ICD", "PTY-01")
    errs = InputValidator.validate_container(c, sample_vessels)
    assert any("Unknown vessel_id" in e for e in errs)


def test_validation_invalid_block_geometry():
    """Yard block with non-positive dimensions or capacity is rejected."""
    b = YardBlock("INV-01", ContainerType.DRY, rows=0, bays_per_row=10, max_tiers=5, capacity_teu=0, plug_points=0)
    errs = InputValidator.validate_yard_block(b)
    assert len(errs) > 0


def test_validation_invalid_state_transition():
    """Invalid container lifecycle transitions are rejected."""
    # Cannot go directly from DISCHARGED to EMPTY_RETURNED
    assert InputValidator.validate_state_transition(ContainerState.DISCHARGED, ContainerState.EMPTY_RETURNED) is False
    # Valid transition: YARD to GATE_OUT
    assert InputValidator.validate_state_transition(ContainerState.YARD, ContainerState.GATE_OUT) is True
    # Valid transition: GATE_OUT to EMPTY_RETURNED
    assert InputValidator.validate_state_transition(ContainerState.GATE_OUT, ContainerState.EMPTY_RETURNED) is True

