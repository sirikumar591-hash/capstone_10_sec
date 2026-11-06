"""
Tests for BR-12: Allocation and Billing Precedence.
"""
from datetime import date, datetime
from decimal import Decimal
import pytest
from src.models.container import Container
from src.models.tariff import TariffItem, TariffTable
from src.models.yard_block import YardBlock
from src.services.demurrage_service import DemurrageService
from src.services.free_days_service import FreeDaysService
from src.services.yard_allocator import YardAllocator
from src.utils.constants import ChargeCode, ContainerType, Direction


def test_BR12_allocation_precedence():
    """
    Allocation Precedence:
    Type/segregation -> Weight/tier -> Same-vessel grouping -> Occupancy -> Overflow.
    """
    # Block 1 matches grouping (VSL-01/Hubballi) but is full on Tier 1
    # Overweight container cannot go to Tier 2 in Block 1 despite grouping!
    b1 = YardBlock("DR-01", ContainerType.DRY, rows=1, bays_per_row=1, max_tiers=2, capacity_teu=2, plug_points=0)
    b2 = YardBlock("DR-02", ContainerType.DRY, rows=1, bays_per_row=2, max_tiers=2, capacity_teu=4, plug_points=0)
    blocks = {"DR-01": b1, "DR-02": b2}
    containers = {}
    allocator = YardAllocator(blocks, containers)

    # b1 has tier 1 occupied
    b1.allocate("OLD_BOX", 20, 1, 1, 1)
    c_old = Container("OLD_BOX", 20, ContainerType.DRY, Decimal("10.00"), Direction.IMPORT, "VSL-01", "KVL", "Hubballi", "PTY-01")
    containers["OLD_BOX"] = c_old

    # New overweight box (>28t) for VSL-01/Hubballi
    # Even though b1 has same vessel/dest grouping, b1 has NO available tier 1 slot.
    # Therefore, weight/tier rule takes precedence and routes to b2!
    c_heavy = Container("HEAVY", 20, ContainerType.DRY, Decimal("29.00"), Direction.IMPORT, "VSL-01", "KVL", "Hubballi", "PTY-01")
    containers["HEAVY"] = c_heavy

    b_id, row, bay, tier = allocator.allocate_container(c_heavy)
    assert b_id == "DR-02"
    assert tier == 1


def test_BR12_billing_precedence():
    """
    Billing Precedence:
    Free days -> Demurrage slabs -> Examination waiver -> Long-stay cap.
    """
    tariff = TariffTable([
        TariffItem(ChargeCode.DEMURRAGE_DRY.value, Decimal("1200.00"), "per day", 20, 1, 5),
        TariffItem(ChargeCode.DEMURRAGE_DRY.value, Decimal("2000.00"), "per day", 20, 6, 10),
        TariffItem(ChargeCode.DEMURRAGE_DRY.value, Decimal("3500.00"), "per day", 20, 11, None),
        TariffItem(ChargeCode.AUCTION_PROCESSING.value, Decimal("10000.00"), "per container"),
    ])
    holidays = set()
    free_days = FreeDaysService(holidays, {("IMPORT", "DRY"): 3})
    dem_service = DemurrageService(tariff, free_days)

    c = Container("C01", 20, ContainerType.DRY, Decimal("15.00"), Direction.IMPORT, "VSL-01", "KVL", "ICD", "PTY-01")
    c.discharge_ts = datetime(2026, 8, 1, 10, 0, 0)
    # 3 days customs exam: Aug 6 to Aug 9 (duration > 2 days -> waiver applies)
    c.exam_start_ts = datetime(2026, 8, 6, 10, 0, 0)
    c.exam_end_ts = datetime(2026, 8, 9, 10, 0, 0)

    # Free days end Aug 4. Demurrage starts Aug 5.
    # Evaluated on Aug 10:
    # Aug 5: Day 1 (1200)
    # Aug 6-9: Waived (3 days)
    # Aug 10: Day 2 (1200)
    # Total demurrage = 2400
    res = dem_service.calculate_demurrage(c, datetime(2026, 8, 10, 12, 0, 0))
    assert res.waived_days == 4  # Aug 6, 7, 8, 9 overlap with demurrage period
    assert res.capped_demurrage == Decimal("2400.00")

