"""
Tests for BR-02: Yard Allocation Priority and Overflow.
"""
from decimal import Decimal
import pytest
from src.models.container import Container
from src.models.yard_block import YardBlock
from src.services.yard_allocator import YardAllocator
from src.utils.constants import ContainerType, Direction, Flag


def test_BR02_same_vessel_destination_grouping():
    """Prefer block containing the most containers of same vessel & destination."""
    b1 = YardBlock("DR-01", ContainerType.DRY, rows=1, bays_per_row=10, max_tiers=1, capacity_teu=10, plug_points=0)
    b2 = YardBlock("DR-02", ContainerType.DRY, rows=1, bays_per_row=10, max_tiers=1, capacity_teu=10, plug_points=0)
    blocks = {"DR-01": b1, "DR-02": b2}
    containers = {}
    allocator = YardAllocator(blocks, containers)

    # b1 already has 2 containers for VSL-01 / Mangaluru
    c1 = Container("C1", 20, ContainerType.DRY, Decimal("10.00"), Direction.IMPORT, "VSL-01", "KVL", "Mangaluru", "PTY-01")
    c2 = Container("C2", 20, ContainerType.DRY, Decimal("10.00"), Direction.IMPORT, "VSL-01", "KVL", "Mangaluru", "PTY-01")
    containers["C1"] = c1
    containers["C2"] = c2
    b1.allocate("C1", 20, 1, 1, 1)
    b1.allocate("C2", 20, 1, 2, 1)

    # New incoming container with same vessel & destination
    c_new = Container("C_NEW", 20, ContainerType.DRY, Decimal("10.00"), Direction.IMPORT, "VSL-01", "KVL", "Mangaluru", "PTY-01")
    containers["C_NEW"] = c_new

    allocated_block, row, bay, tier = allocator.allocate_container(c_new)
    assert allocated_block == "DR-01"


def test_BR02_lowest_occupancy_and_tie_break():
    """If grouping is equal, prefer block with lowest occupancy, then lowest block_id."""
    b1 = YardBlock("DR-01", ContainerType.DRY, rows=1, bays_per_row=10, max_tiers=1, capacity_teu=10, plug_points=0)
    b2 = YardBlock("DR-02", ContainerType.DRY, rows=1, bays_per_row=10, max_tiers=1, capacity_teu=10, plug_points=0)
    blocks = {"DR-01": b1, "DR-02": b2}
    containers = {}
    allocator = YardAllocator(blocks, containers)

    # b1 has 1 container, b2 has 0 containers
    c1 = Container("C1", 20, ContainerType.DRY, Decimal("10.00"), Direction.IMPORT, "VSL-01", "KVL", "Hubballi", "PTY-01")
    containers["C1"] = c1
    b1.allocate("C1", 20, 1, 1, 1)

    # New container for a different destination should prefer b2 (lowest occupancy)
    c_new = Container("C_NEW", 20, ContainerType.DRY, Decimal("10.00"), Direction.IMPORT, "VSL-02", "DSL", "Mysuru", "PTY-02")
    containers["C_NEW"] = c_new
    allocated_block, _, _, _ = allocator.allocate_container(c_new)
    assert allocated_block == "DR-02"


def test_BR02_overflow_fallback():
    """When all blocks are full, allocate to OVERFLOW with flag."""
    b1 = YardBlock("DR-01", ContainerType.DRY, rows=1, bays_per_row=1, max_tiers=1, capacity_teu=1, plug_points=0)
    blocks = {"DR-01": b1}
    containers = {}
    allocator = YardAllocator(blocks, containers)

    # Fill b1
    c1 = Container("C1", 20, ContainerType.DRY, Decimal("10.00"), Direction.IMPORT, "VSL-01", "KVL", "Hubballi", "PTY-01")
    containers["C1"] = c1
    b1.allocate("C1", 20, 1, 1, 1)

    c2 = Container("C2", 20, ContainerType.DRY, Decimal("10.00"), Direction.IMPORT, "VSL-01", "KVL", "Hubballi", "PTY-01")
    containers["C2"] = c2
    allocated_block, row, bay, tier = allocator.allocate_container(c2)
    assert allocated_block == "OVERFLOW"
    assert Flag.OVERFLOW.value in c2.flags

