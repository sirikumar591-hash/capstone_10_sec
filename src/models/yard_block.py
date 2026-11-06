"""
Domain Model: Yard Block and Slot Allocation Grid.
Implements BR-01 Container Stacking Rules and Slot Geometry.
"""
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple, Set, List
from src.utils.constants import ContainerType


@dataclass
class YardBlock:
    block_id: str
    block_type: ContainerType
    rows: int
    bays_per_row: int
    max_tiers: int
    capacity_teu: int
    plug_points: int

    # Grid mapping: (row, bay, tier) -> container_no
    # For a 40-ft container, both (row, bay, tier) and (row, bay+1, tier) point to the container_no
    grid: Dict[Tuple[int, int, int], str] = field(default_factory=dict)
    # Set of unique container numbers currently in this block
    containers: Set[str] = field(default_factory=set)

    @property
    def teu_used(self) -> int:
        """Total occupied TEU slots in the grid (each grid cell is 1 TEU)."""
        return len(self.grid)

    @property
    def available_teu(self) -> int:
        """Remaining TEU capacity in this block."""
        return self.capacity_teu - self.teu_used

    @property
    def occupancy_pct(self) -> float:
        """Occupancy percentage (0.0 to 100.0)."""
        if self.capacity_teu == 0:
            return 0.0
        return round((self.teu_used / self.capacity_teu) * 100.0, 2)

    def is_slot_empty(self, row: int, bay: int, tier: int) -> bool:
        """Checks if a single slot is empty."""
        return (row, bay, tier) not in self.grid

    def is_slot_supported(self, row: int, bay: int, tier: int) -> bool:
        """
        Rule BR-01: Any tier above 1 must sit on occupied slots.
        Returns True if tier is 1, or if slot at (tier - 1) is occupied.
        """
        if tier == 1:
            return True
        return (row, bay, tier - 1) in self.grid

    def can_place_20ft(self, row: int, bay: int, tier: int) -> bool:
        """Validates if a 20-ft container can be placed at (row, bay, tier)."""
        if row < 1 or row > self.rows or bay < 1 or bay > self.bays_per_row or tier < 1 or tier > self.max_tiers:
            return False
        return self.is_slot_empty(row, bay, tier) and self.is_slot_supported(row, bay, tier)

    def can_place_40ft(self, row: int, bay: int, tier: int) -> bool:
        """
        Rule BR-01: A 40-ft box needs two adjacent bays of the same row and tier,
        and any tier above 1 must sit on occupied slots.
        """
        if bay + 1 > self.bays_per_row:
            return False
        return (
            self.can_place_20ft(row, bay, tier)
            and self.can_place_20ft(row, bay + 1, tier)
        )

    def find_first_available_slot(self, size_ft: int, is_overweight: bool) -> Optional[Tuple[int, int, int]]:
        """
        Finds the first available slot following precedence:
        'lowest tier first, then lowest row, then lowest bay'.
        Overweight containers (> 28t) are restricted to tier 1 only.
        """
        tier_limit = 1 if is_overweight else self.max_tiers

        for tier in range(1, tier_limit + 1):
            for row in range(1, self.rows + 1):
                for bay in range(1, self.bays_per_row + 1):
                    if size_ft == 20:
                        if self.can_place_20ft(row, bay, tier):
                            return (row, bay, tier)
                    elif size_ft == 40:
                        if self.can_place_40ft(row, bay, tier):
                            return (row, bay, tier)
        return None

    def allocate(self, container_no: str, size_ft: int, row: int, bay: int, tier: int) -> None:
        """Places a container into the block grid."""
        self.grid[(row, bay, tier)] = container_no
        if size_ft == 40:
            self.grid[(row, bay + 1, tier)] = container_no
        self.containers.add(container_no)

    def deallocate(self, container_no: str) -> None:
        """Removes a container from the block grid."""
        slots_to_remove = [k for k, v in self.grid.items() if v == container_no]
        for slot in slots_to_remove:
            del self.grid[slot]
        self.containers.discard(container_no)
