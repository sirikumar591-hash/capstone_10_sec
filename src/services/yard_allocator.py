"""
Service: Yard Allocator.
Implements BR-01 (Container Stacking), BR-02 (Allocation Priority), and BR-12 (Precedence).
"""
from typing import Dict, List, Optional, Tuple
from src.models.container import Container
from src.models.yard_block import YardBlock
from src.utils.constants import ContainerType, Flag


class YardAllocator:
    def __init__(self, blocks: Dict[str, YardBlock], containers_map: Dict[str, Container]):
        self.blocks = blocks
        self.containers_map = containers_map

    def check_imo_segregation(self, block: YardBlock, incoming_imo: Optional[str]) -> bool:
        """
        BR-01 Segregation Rule:
        IMO classes 1 and 5.1 cannot share a block with IMO class 3.
        """
        if not incoming_imo:
            return True

        current_imos = set()
        for c_no in block.containers:
            c = self.containers_map.get(c_no)
            if c and c.imo_class:
                current_imos.add(str(c.imo_class).strip())

        if incoming_imo in {"1", "5.1"}:
            if "3" in current_imos:
                return False
        elif incoming_imo == "3":
            if "1" in current_imos or "5.1" in current_imos:
                return False

        return True

    def is_block_compatible(self, block: YardBlock, container: Container) -> bool:
        """
        BR-01: Verifies block type compatibility, capacity, plug points, and segregation.
        """
        # Block type matching
        if container.container_type == ContainerType.EMPTY:
            if block.block_type != ContainerType.EMPTY:
                return False
        elif container.container_type == ContainerType.REEFER:
            if block.block_type != ContainerType.REEFER:
                return False
            # Check available plug points
            if len(block.containers) >= block.plug_points:
                return False
        elif container.container_type == ContainerType.HAZ:
            if block.block_type != ContainerType.HAZ:
                return False
            if not self.check_imo_segregation(block, container.imo_class):
                return False
        elif container.container_type == ContainerType.DRY:
            if block.block_type != ContainerType.DRY:
                return False

        # Capacity check in TEU
        if block.available_teu < container.teu:
            return False

        return True

    def allocate_container(self, container: Container, reason: str = "ALLOCATION") -> Tuple[str, int, int, int]:
        """
        Allocates a container according to BR-01, BR-02, and BR-12.
        Precedence:
        1. Type & segregation compatibility
        2. Weight and tier restrictions
        3. Same-vessel and destination grouping
        4. Lowest occupancy
        5. Lowest block ID
        6. Fallback to OVERFLOW
        Returns (block_id, row, bay, tier).
        """
        candidate_blocks: List[YardBlock] = []

        for block in self.blocks.values():
            if self.is_block_compatible(block, container):
                candidate_blocks.append(block)

        # Sort candidate blocks by:
        # 1. Same vessel and destination count (descending)
        # 2. Occupancy ratio (ascending)
        # 3. Block ID (ascending)
        def sort_key(b: YardBlock):
            same_group_count = 0
            for c_no in b.containers:
                other = self.containers_map.get(c_no)
                if other and other.vessel_id == container.vessel_id and other.destination == container.destination:
                    same_group_count += 1
            
            occupancy_ratio = b.teu_used / b.capacity_teu if b.capacity_teu > 0 else 1.0
            return (-same_group_count, occupancy_ratio, b.block_id)

        candidate_blocks.sort(key=sort_key)

        for block in candidate_blocks:
            slot = block.find_first_available_slot(container.size_ft, container.is_overweight)
            if slot:
                row, bay, tier = slot
                block.allocate(container.container_no, container.size_ft, row, bay, tier)
                container.current_block = block.block_id
                container.current_row = row
                container.current_bay = bay
                container.current_tier = tier
                return (block.block_id, row, bay, tier)

        # No valid block or tier slot found -> OVERFLOW
        container.flags.add(Flag.OVERFLOW.value)
        container.current_block = "OVERFLOW"
        container.current_row = 0
        container.current_bay = 0
        container.current_tier = 0
        return ("OVERFLOW", 0, 0, 0)

    def deallocate_container(self, container: Container) -> None:
        """Removes container from yard block grid."""
        if container.current_block and container.current_block in self.blocks:
            self.blocks[container.current_block].deallocate(container.container_no)
        container.current_block = None
        container.current_row = None
        container.current_bay = None
        container.current_tier = None

