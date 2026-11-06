"""
Input and Business Validator.
Performs strict validation on all input data, events, and business constraints.
"""
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, List, Optional, Set
from src.models.container import Container
from src.models.yard_block import YardBlock
from src.models.vessel import Vessel
from src.utils.constants import ContainerType, Direction, ContainerState


class ValidationError(Exception):
    """Custom exception for validation errors."""
    pass


class InputValidator:
    VALID_SIZES = {20, 40}
    VALID_TYPES = {ContainerType.DRY, ContainerType.REEFER, ContainerType.HAZ, ContainerType.EMPTY}
    VALID_IMO_CLASSES = {"1", "3", "5.1", "6.1", "8", "9"}

    @classmethod
    def validate_container(cls, container: Container, vessels: Dict[str, Vessel]) -> List[str]:
        """Validates container master record. Returns list of error messages (if any)."""
        errors = []
        if not container.container_no or len(container.container_no) < 4:
            errors.append(f"Invalid container number: {container.container_no}")

        if container.size_ft not in cls.VALID_SIZES:
            errors.append(f"Invalid size {container.size_ft} for container {container.container_no}. Allowed: 20, 40")

        if container.container_type not in cls.VALID_TYPES:
            errors.append(f"Invalid container type {container.container_type} for container {container.container_no}")

        if container.gross_weight_t < Decimal("0.00"):
            errors.append(f"Negative gross weight {container.gross_weight_t} for container {container.container_no}")

        if container.container_type == ContainerType.HAZ:
            if not container.imo_class or container.imo_class not in cls.VALID_IMO_CLASSES:
                errors.append(f"HAZ container {container.container_no} missing or invalid IMO class: {container.imo_class}")

        if container.vessel_id not in vessels:
            errors.append(f"Unknown vessel_id {container.vessel_id} for container {container.container_no}")

        return errors

    @classmethod
    def validate_yard_block(cls, block: YardBlock) -> List[str]:
        """Validates yard block configuration."""
        errors = []
        if block.rows <= 0 or block.bays_per_row <= 0 or block.max_tiers <= 0:
            errors.append(f"Invalid geometry for block {block.block_id}: rows={block.rows}, bays={block.bays_per_row}, tiers={block.max_tiers}")
        if block.capacity_teu <= 0:
            errors.append(f"Invalid capacity for block {block.block_id}: {block.capacity_teu}")
        return errors

    @classmethod
    def validate_state_transition(cls, current_state: Optional[ContainerState], new_state: ContainerState) -> bool:
        """
        Validates container lifecycle state transitions:
        - None -> DISCHARGED or YARD
        - DISCHARGED -> YARD
        - YARD -> GATE_OUT, RESTOWED, LOADED, AUCTION_LISTED
        - RESTOWED -> YARD, GATE_OUT, LOADED
        - GATE_OUT -> EMPTY_RETURNED
        - EMPTY_RETURNED -> YARD (in EMPTY block)
        - AUCTION_LISTED -> GATE_OUT (with delisting fee)
        """
        if current_state is None:
            return new_state in {ContainerState.DISCHARGED, ContainerState.YARD}
        
        valid_transitions = {
            ContainerState.DISCHARGED: {ContainerState.YARD, ContainerState.AUCTION_LISTED},
            ContainerState.YARD: {ContainerState.GATE_OUT, ContainerState.RESTOWED, ContainerState.LOADED, ContainerState.AUCTION_LISTED},
            ContainerState.RESTOWED: {ContainerState.YARD, ContainerState.GATE_OUT, ContainerState.LOADED, ContainerState.AUCTION_LISTED},
            ContainerState.AUCTION_LISTED: {ContainerState.GATE_OUT, ContainerState.RESTOWED},
            ContainerState.GATE_OUT: {ContainerState.EMPTY_RETURNED},
            ContainerState.EMPTY_RETURNED: {ContainerState.YARD},
            ContainerState.LOADED: set(),
        }

        allowed = valid_transitions.get(current_state, set())
        return new_state in allowed

