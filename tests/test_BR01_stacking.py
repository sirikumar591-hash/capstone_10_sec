"""
Tests for BR-01: Container Stacking Rules.
"""
from decimal import Decimal
import pytest
from src.models.container import Container
from src.models.yard_block import YardBlock
from src.services.yard_allocator import YardAllocator
from src.utils.constants import ContainerType, Direction


def test_BR01_teu_calculation():
    """20-ft = 1 TEU, 40-ft = 2 TEU."""
    c20 = Container("C20", 20, ContainerType.DRY, Decimal("15.00"), Direction.IMPORT, "VSL-01", "KVL", "ICD", "PTY-01")
    c40 = Container("C40", 40, ContainerType.DRY, Decimal("20.00"), Direction.IMPORT, "VSL-01", "KVL", "ICD", "PTY-01")
    assert c20.teu == 1
    assert c40.teu == 2


def test_BR01_reefer_only_in_reefer_block_with_plug():
    """REEFER containers require reefer blocks with plug points."""
    rf_block = YardBlock("RF-01", ContainerType.REEFER, rows=2, bays_per_row=8, max_tiers=3, capacity_teu=48, plug_points=48)
    dry_block = YardBlock("DR-01", ContainerType.DRY, rows=2, bays_per_row=10, max_tiers=5, capacity_teu=100, plug_points=0)
    
    blocks = {"RF-01": rf_block, "DR-01": dry_block}
    containers = {}
    allocator = YardAllocator(blocks, containers)

    reefer_box = Container("RF01", 20, ContainerType.REEFER, Decimal("18.00"), Direction.IMPORT, "VSL-01", "KVL", "ICD", "PTY-01", set_temp_c=Decimal("-18.00"))
    containers["RF01"] = reefer_box

    assert allocator.is_block_compatible(dry_block, reefer_box) is False
    assert allocator.is_block_compatible(rf_block, reefer_box) is True


def test_BR01_hazardous_segregation():
    """IMO classes 1 and 5.1 cannot share a block with IMO class 3."""
    hz_block = YardBlock("HZ-01", ContainerType.HAZ, rows=2, bays_per_row=5, max_tiers=2, capacity_teu=20, plug_points=0)
    blocks = {"HZ-01": hz_block}
    containers = {}
    allocator = YardAllocator(blocks, containers)

    # Class 5.1 container occupies HZ-01
    c_51 = Container("HAZ_51", 20, ContainerType.HAZ, Decimal("15.00"), Direction.IMPORT, "VSL-01", "KVL", "ICD", "PTY-01", imo_class="5.1")
    containers["HAZ_51"] = c_51
    hz_block.allocate("HAZ_51", 20, 1, 1, 1)

    # Incoming Class 3 container must be rejected
    c_3 = Container("HAZ_3", 20, ContainerType.HAZ, Decimal("15.00"), Direction.IMPORT, "VSL-02", "DSL", "ICD", "PTY-02", imo_class="3")
    containers["HAZ_3"] = c_3

    assert allocator.check_imo_segregation(hz_block, c_3.imo_class) is False
    assert allocator.is_block_compatible(hz_block, c_3) is False

    # Incoming Class 1 container CAN share with 5.1
    c_1 = Container("HAZ_1", 20, ContainerType.HAZ, Decimal("15.00"), Direction.IMPORT, "VSL-03", "ARL", "ICD", "PTY-03", imo_class="1")
    containers["HAZ_1"] = c_1
    assert allocator.check_imo_segregation(hz_block, c_1.imo_class) is True


def test_BR01_tier_limits_and_overweight_tier1():
    """Heavy containers (> 28t) must be placed at tier 1 only."""
    heavy_box = Container("HEAVY", 40, ContainerType.DRY, Decimal("29.50"), Direction.IMPORT, "VSL-01", "KVL", "ICD", "PTY-01")
    assert heavy_box.is_overweight is True

    block = YardBlock("DR-01", ContainerType.DRY, rows=1, bays_per_row=2, max_tiers=2, capacity_teu=4, plug_points=0)
    # Put a container on Tier 1
    block.allocate("BOX1", 40, 1, 1, 1)
    
    # Try finding slot for heavy box: Tier 1 is occupied, Tier 2 cannot take overweight box!
    slot = block.find_first_available_slot(heavy_box.size_ft, heavy_box.is_overweight)
    assert slot is None

