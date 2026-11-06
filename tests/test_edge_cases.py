"""
Tests for Official Planted Edge Cases (EC-01 to EC-08).
Verifies the exact edge cases and container records documented in README.md.
"""
from datetime import date, datetime
from decimal import Decimal
import pytest
from src.models.container import Container
from src.models.tariff import TariffItem, TariffTable
from src.models.yard_block import YardBlock
from src.services.demurrage_service import DemurrageService
from src.services.detention_service import DetentionService
from src.services.free_days_service import FreeDaysService
from src.services.reefer_service import ReeferService
from src.services.yard_allocator import YardAllocator
from src.utils.constants import ChargeCode, ContainerType, Direction, Flag


@pytest.fixture
def official_tariff():
    items = [
        TariffItem(ChargeCode.DEMURRAGE_DRY.value, Decimal("1200.00"), "per day", 20, 1, 5),
        TariffItem(ChargeCode.DEMURRAGE_DRY.value, Decimal("2000.00"), "per day", 20, 6, 10),
        TariffItem(ChargeCode.DEMURRAGE_DRY.value, Decimal("3500.00"), "per day", 20, 11, None),
        TariffItem(ChargeCode.SIZE_MULT_40.value, Decimal("1.60"), "multiplier", 40),
        TariffItem(ChargeCode.TYPE_MULT_REEFER.value, Decimal("2.00"), "multiplier"),
        TariffItem(ChargeCode.TYPE_MULT_HAZ.value, Decimal("1.50"), "multiplier"),
        TariffItem(ChargeCode.REEFER_PLUG.value, Decimal("2500.00"), "per day"),
        TariffItem(ChargeCode.DETENTION.value, Decimal("1500.00"), "per day", 20, 8, 14),
        TariffItem(ChargeCode.DETENTION.value, Decimal("2800.00"), "per day", 40, 8, 14),
        TariffItem(ChargeCode.AUCTION_PROCESSING.value, Decimal("10000.00"), "per container"),
        TariffItem(ChargeCode.DELISTING.value, Decimal("2000.00"), "per container"),
    ]
    return TariffTable(items)


def test_EC01_last_free_day_sunday_monday_holiday():
    """
    EC-01: KVLU5744158 (VSL-04 import, DRY 20):
    Discharge: 2026-09-10 14:00.
    3 free days end Sun 2026-09-13 -> extend past Sun to Mon 2026-09-14 (Ganesh Chaturthi)
    -> last free day Tue 2026-09-15. Demurrage starts 2026-09-16.
    Gate-out: 2026-09-18 11:30 (3 days demurrage).
    """
    holidays = {date(2026, 9, 14)}
    free_days = FreeDaysService(holidays, {("IMPORT", "DRY"): 3})
    discharge_ts = datetime(2026, 9, 10, 14, 0, 0)
    last_free = free_days.calculate_import_last_free_day(discharge_ts, ContainerType.DRY)
    assert last_free == date(2026, 9, 15)


def test_EC02_gate_out_at_0005_day_6(official_tariff):
    """
    EC-02: DCSU7125204 (40-ft DRY, VSL-02):
    Last free day: 2026-08-17.
    GATE_OUT at 2026-08-23 00:05 = 5 minutes into demurrage day 6.
    Day 6 counts as full day at slab-2 rate (x1.6 for 40-ft).
    5 days slab 1 @ 1920 + 1 day slab 2 @ 3200 = 12,800.00.
    """
    holidays = set()
    free_days = FreeDaysService(holidays, {("IMPORT", "DRY"): 3})
    dem_service = DemurrageService(official_tariff, free_days)

    c = Container("DCSU7125204", 40, ContainerType.DRY, Decimal("20.00"), Direction.IMPORT, "VSL-02", "DSL", "ICD", "PTY-01")
    c.discharge_ts = datetime(2026, 8, 14, 10, 0, 0)
    gate_out_ts = datetime(2026, 8, 23, 0, 5, 0)

    res = dem_service.calculate_demurrage(c, gate_out_ts)
    assert res.net_chargeable_days == 6
    assert res.capped_demurrage == Decimal("12800.00")


def test_EC03_imo_class_3_vs_class_5_1_segregation():
    """
    EC-03: DCSU3143954 (IMO class 3, VSL-02) arrives while HZ-01 holds class 5.1 (KVLU6134069).
    Segregation forbids HZ-01, allocate to HZ-02.
    """
    hz01 = YardBlock("HZ-01", ContainerType.HAZ, rows=2, bays_per_row=5, max_tiers=2, capacity_teu=20, plug_points=0)
    hz02 = YardBlock("HZ-02", ContainerType.HAZ, rows=2, bays_per_row=5, max_tiers=2, capacity_teu=20, plug_points=0)
    blocks = {"HZ-01": hz01, "HZ-02": hz02}
    containers = {}
    allocator = YardAllocator(blocks, containers)

    # HZ-01 holds Class 5.1
    c_51 = Container("KVLU6134069", 20, ContainerType.HAZ, Decimal("15.00"), Direction.IMPORT, "VSL-01", "KVL", "ICD", "PTY-01", imo_class="5.1")
    containers["KVLU6134069"] = c_51
    hz01.allocate("KVLU6134069", 20, 1, 1, 1)

    # Class 3 arrives
    c_3 = Container("DCSU3143954", 20, ContainerType.HAZ, Decimal("15.00"), Direction.IMPORT, "VSL-02", "DSL", "ICD", "PTY-02", imo_class="3")
    containers["DCSU3143954"] = c_3

    b_id, row, bay, tier = allocator.allocate_container(c_3)
    assert b_id == "HZ-02"


def test_EC04_overweight_tier1_allocation_fallback():
    """
    EC-04: ARLU1838149 (40-ft DRY, 29.40 t > 28 t, VSL-03 -> CFS Mangaluru):
    Tier 1 of DR-01 is full -> routes to next valid block (DR-04).
    """
    dr01 = YardBlock("DR-01", ContainerType.DRY, rows=1, bays_per_row=2, max_tiers=2, capacity_teu=4, plug_points=0)
    dr04 = YardBlock("DR-04", ContainerType.DRY, rows=1, bays_per_row=2, max_tiers=2, capacity_teu=4, plug_points=0)
    blocks = {"DR-01": dr01, "DR-04": dr04}
    containers = {}
    allocator = YardAllocator(blocks, containers)

    # Fill tier 1 of DR-01
    dr01.allocate("OLD_40", 40, 1, 1, 1)

    c_heavy = Container("ARLU1838149", 40, ContainerType.DRY, Decimal("29.40"), Direction.IMPORT, "VSL-03", "ARL", "CFS Mangaluru", "PTY-01")
    containers["ARLU1838149"] = c_heavy

    b_id, row, bay, tier = allocator.allocate_container(c_heavy)
    assert b_id == "DR-04"
    assert tier == 1


def test_EC05_customs_exam_boundary(official_tariff):
    """
    EC-05: DCSU1162695: exam exactly 2 days (48h) -> NO waiver.
    DCSU9027105: exam for 3 days (72h) -> waiver applied.
    """
    holidays = set()
    free_days = FreeDaysService(holidays, {("IMPORT", "DRY"): 3})
    dem_service = DemurrageService(official_tariff, free_days)

    # Exactly 2 days: Aug 14 12:00 to Aug 16 12:00
    c_exact = Container("DCSU1162695", 20, ContainerType.DRY, Decimal("15.00"), Direction.IMPORT, "VSL-02", "DSL", "ICD", "PTY-01")
    c_exact.discharge_ts = datetime(2026, 8, 10, 12, 0, 0)
    c_exact.exam_start_ts = datetime(2026, 8, 14, 12, 0, 0)
    c_exact.exam_end_ts = datetime(2026, 8, 16, 12, 0, 0)  # Exactly 48 hours
    res_exact = dem_service.calculate_demurrage(c_exact, datetime(2026, 8, 20, 12, 0, 0))
    assert res_exact.waived_days == 0

    # 3 days: Aug 14 12:00 to Aug 17 12:00 (72h > 48h)
    c_3days = Container("DCSU9027105", 20, ContainerType.DRY, Decimal("15.00"), Direction.IMPORT, "VSL-02", "DSL", "ICD", "PTY-01")
    c_3days.discharge_ts = datetime(2026, 8, 10, 12, 0, 0)
    c_3days.exam_start_ts = datetime(2026, 8, 14, 12, 0, 0)
    c_3days.exam_end_ts = datetime(2026, 8, 17, 12, 0, 0)
    res_3days = dem_service.calculate_demurrage(c_3days, datetime(2026, 8, 20, 12, 0, 0))
    assert res_3days.waived_days > 0


def test_EC06_long_stay_cap_and_auction_fee(official_tariff):
    """
    EC-06: KVLU6594605 (VSL-01, discharged 2026-08-03 18:00) never gates out:
    AUCTION_LISTED after 30 days in yard; from day 45 capped at slab-3 rate x 45 days
    + Rs 10000 auction processing fee.
    """
    holidays = set()
    free_days = FreeDaysService(holidays, {("IMPORT", "DRY"): 3})
    dem_service = DemurrageService(official_tariff, free_days)

    c = Container("KVLU6594605", 20, ContainerType.DRY, Decimal("15.00"), Direction.IMPORT, "VSL-01", "KVL", "ICD", "PTY-01")
    c.discharge_ts = datetime(2026, 8, 3, 18, 0, 0)

    # On 2026-09-29 (57 days in yard)
    res = dem_service.calculate_demurrage(c, datetime(2026, 9, 29, 12, 0, 0))
    assert res.is_auction_listed is True
    assert res.is_capped is True
    # Slab 3 base = 3500. Cap = 3500 * 45 = 157500.00
    assert res.capped_demurrage == Decimal("157500.00")
    assert res.auction_fee == Decimal("10000.00")


def test_EC07_empty_return_seventh_day(official_tariff):
    """
    EC-07: KVLU8300071 (40-ft):
    GATE_OUT then EMPTY_RETURN on 7th day after gate-out -> within 7 free detention days, no detention.
    """
    service = DetentionService(official_tariff)
    c = Container("KVLU8300071", 40, ContainerType.DRY, Decimal("20.00"), Direction.IMPORT, "VSL-01", "KVL", "ICD", "PTY-01")
    c.gate_out_ts = datetime(2026, 8, 4, 13, 0, 0)
    c.empty_return_ts = datetime(2026, 8, 11, 12, 0, 0)  # 7 days later

    res = service.calculate_detention(c, datetime(2026, 8, 30))
    assert res.chargeable_days == 0
    assert res.detention_amount == Decimal("0.00")


def test_EC08_reefer_temp_deviation_boundary(official_tariff):
    """
    EC-08: ARLU5557223 (reefer): 4h deviation -> NO CLAIM_RISK, no pause.
    ARLU8302265: 5h deviation -> CLAIM_RISK and 5h pause.
    """
    service = ReeferService(official_tariff)

    # Exactly 4 hours
    c_4h = Container("ARLU5557223", 20, ContainerType.REEFER, Decimal("15.00"), Direction.IMPORT, "VSL-03", "ARL", "ICD", "PTY-01")
    c_4h.discharge_ts = datetime(2026, 8, 26, 10, 0, 0)
    flagged_4h = service.process_temperature_deviation(
        c_4h, datetime(2026, 8, 27, 8, 0, 0), datetime(2026, 8, 27, 12, 0, 0), Decimal("10.00")
    )
    assert flagged_4h is False
    assert Flag.CLAIM_RISK.value not in c_4h.flags

    # 5 hours
    c_5h = Container("ARLU8302265", 20, ContainerType.REEFER, Decimal("15.00"), Direction.IMPORT, "VSL-03", "ARL", "ICD", "PTY-01")
    c_5h.discharge_ts = datetime(2026, 8, 26, 10, 0, 0)
    flagged_5h = service.process_temperature_deviation(
        c_5h, datetime(2026, 8, 27, 8, 0, 0), datetime(2026, 8, 27, 13, 0, 0), Decimal("12.00")
    )
    assert flagged_5h is True
    assert Flag.CLAIM_RISK.value in c_5h.flags

