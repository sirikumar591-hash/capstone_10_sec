"""
Domain Model: Container Entity.
Tracks container physical specs, yard location, dynamic operational state, and history.
"""
from dataclasses import dataclass, field
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, Set, List, Tuple
from src.utils.constants import ContainerType, Direction, ContainerState, ShutOutReason
from src.utils.money_utils import to_decimal


@dataclass
class Container:
    container_no: str
    size_ft: int
    container_type: ContainerType
    gross_weight_t: Decimal
    direction: Direction
    vessel_id: str
    line_code: str
    destination: str
    party_id: str
    imo_class: Optional[str] = None
    set_temp_c: Optional[Decimal] = None

    # Operational state tracking
    state: Optional[ContainerState] = None
    current_block: Optional[str] = None
    current_row: Optional[int] = None
    current_bay: Optional[int] = None
    current_tier: Optional[int] = None

    # Timestamps
    discharge_ts: Optional[datetime] = None
    gate_in_ts: Optional[datetime] = None
    gate_out_ts: Optional[datetime] = None
    empty_return_ts: Optional[datetime] = None
    load_ts: Optional[datetime] = None
    exam_start_ts: Optional[datetime] = None
    exam_end_ts: Optional[datetime] = None
    shut_out_ts: Optional[datetime] = None
    shut_out_reason: Optional[ShutOutReason] = None

    # Financial and approval tracking
    manager_approved: bool = False
    manager_approve_date: Optional[date] = None
    flags: Set[str] = field(default_factory=set)
    temperature_deviations: List[Tuple[datetime, datetime, Decimal]] = field(default_factory=list)

    # Restow history
    restow_count: int = 0
    auction_listed: bool = False
    delisted: bool = False

    @property
    def teu(self) -> int:
        """20-ft = 1 TEU, 40-ft = 2 TEU."""
        return 1 if self.size_ft == 20 else 2

    @property
    def is_overweight(self) -> bool:
        """Containers weighing more than 28 tonnes must be placed at tier 1."""
        return self.gross_weight_t > Decimal("28.00")
