"""
Service: Demurrage and Storage Calculation.
Implements BR-04 (Demurrage Slabs & Multipliers), BR-06 (Exam Waivers), BR-09 (Long-stay Cap & Auction), and BR-12 (Precedence).
"""
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Set, Tuple
from src.models.container import Container
from src.models.tariff import TariffTable
from src.services.free_days_service import FreeDaysService
from src.utils.constants import ChargeCode, ContainerType, ContainerState, Flag
from src.utils.money_utils import round_money, to_decimal


@dataclass
class DemurrageResult:
    chargeable_days: int
    waived_days: int
    net_chargeable_days: int
    base_demurrage: Decimal
    capped_demurrage: Decimal
    auction_fee: Decimal
    delisting_fee: Decimal
    is_auction_listed: bool
    is_capped: bool


class DemurrageService:
    def __init__(self, tariff: TariffTable, free_days_service: FreeDaysService):
        self.tariff = tariff
        self.free_days_service = free_days_service

    def get_effective_daily_rate(self, day_number: int, container: Container) -> Decimal:
        """
        Calculates daily demurrage rate for a specific day number after free days end,
        incorporating size (40-ft), type (REEFER/HAZ), and OVERFLOW multipliers.
        """
        # Base rate (20-ft DRY)
        base = self.tariff.get_demurrage_rate(day_number, container.size_ft)
        
        # Type multiplier
        if container.container_type == ContainerType.REEFER:
            mult = self.tariff.get_multiplier(ChargeCode.TYPE_MULT_REEFER.value, Decimal("2.00"))
            base *= mult
        elif container.container_type == ContainerType.HAZ:
            mult = self.tariff.get_multiplier(ChargeCode.TYPE_MULT_HAZ.value, Decimal("1.50"))
            base *= mult

        # Overflow multiplier
        if Flag.OVERFLOW.value in container.flags or container.current_block == "OVERFLOW":
            over_mult = self.tariff.get_multiplier(ChargeCode.OVERFLOW_STORAGE_MULT.value, Decimal("1.50"))
            base *= over_mult

        return round_money(base)

    def calculate_demurrage(
        self,
        container: Container,
        as_of_dt: datetime,
    ) -> DemurrageResult:
        """
        Calculates complete demurrage for a container up to as_of_dt.
        Follows BR-12 Billing Precedence:
        1. Free days & holiday extension
        2. Demurrage slabs
        3. Customs exam waivers
        4. Long-stay cap (from day 45)
        5. Auction & delisting fees
        """
        if not container.discharge_ts:
            return DemurrageResult(0, 0, 0, Decimal("0.00"), Decimal("0.00"), Decimal("0.00"), Decimal("0.00"), False, False)

        discharge_date = container.discharge_ts.date()
        as_of_date = as_of_dt.date()

        # Total days in yard
        total_yard_days = (as_of_date - discharge_date).days
        if as_of_dt.time() > datetime.min.time():
            # Partial day in yard counts as a full day
            total_yard_days += 1

        # Check 30-day AUCTION_LISTED mark
        is_auction = False
        if total_yard_days > 30:
            is_auction = True
            container.auction_listed = True
            if container.state == ContainerState.YARD:
                container.state = ContainerState.AUCTION_LISTED

        # Calculate free days
        last_free_day = self.free_days_service.calculate_import_last_free_day(
            container.discharge_ts, container.container_type
        )

        # Chargeable calendar days start the day after last_free_day
        demurrage_start_date = last_free_day + timedelta(days=1)
        
        if as_of_date < demurrage_start_date:
            # Still within free period
            return DemurrageResult(0, 0, 0, Decimal("0.00"), Decimal("0.00"), Decimal("0.00"), Decimal("0.00"), is_auction, False)

        # Count chargeable days (partial day counts as full day)
        raw_chargeable_days = (as_of_date - demurrage_start_date).days + 1

        # Check Customs Examination Waiver (BR-06)
        waived_exam_days = 0
        if container.exam_start_ts and container.exam_end_ts:
            exam_duration_seconds = (container.exam_end_ts - container.exam_start_ts).total_seconds()
            # Waiver applies only if examination EXCEEDS 2 days (48 hours)
            if exam_duration_seconds > 2 * 86400:
                exam_start_d = container.exam_start_ts.date()
                exam_end_d = container.exam_end_ts.date()
                # Find overlap between [demurrage_start_date, as_of_date] and [exam_start_d, exam_end_d]
                overlap_start = max(demurrage_start_date, exam_start_d)
                overlap_end = min(as_of_date, exam_end_d)
                if overlap_start <= overlap_end:
                    waived_exam_days = (overlap_end - overlap_start).days + 1

        net_chargeable_days = max(0, raw_chargeable_days - waived_exam_days)

        # Accumulate demurrage through slabs
        total_demurrage = Decimal("0.00")
        current_chargeable_day = 1
        curr_d = demurrage_start_date
        while curr_d <= as_of_date:
            # Check if this day is within an examination waiver
            is_waived = False
            if container.exam_start_ts and container.exam_end_ts:
                exam_duration_seconds = (container.exam_end_ts - container.exam_start_ts).total_seconds()
                if exam_duration_seconds > 2 * 86400:
                    if container.exam_start_ts.date() <= curr_d <= container.exam_end_ts.date():
                        is_waived = True

            if not is_waived:
                daily_rate = self.get_effective_daily_rate(current_chargeable_day, container)
                total_demurrage += daily_rate
                current_chargeable_day += 1

            curr_d += timedelta(days=1)

        # BR-09: Long-stay cap from Day 45
        # Cap = Slab-3 daily rate * 45 days
        is_capped = False
        slab3_rate = self.get_effective_daily_rate(11, container)
        max_cap = slab3_rate * Decimal("45")

        auction_fee = Decimal("0.00")
        delisting_fee = Decimal("0.00")

        if total_yard_days >= 45:
            if total_demurrage > max_cap:
                total_demurrage = max_cap
                is_capped = True
            auction_fee = self.tariff.get_flat_rate(ChargeCode.AUCTION_PROCESSING.value)

        # Delisting fee if container gates out after being auction-listed
        if container.auction_listed and container.gate_out_ts:
            delisting_fee = self.tariff.get_flat_rate(ChargeCode.DELISTING.value)
            container.delisted = True

        return DemurrageResult(
            chargeable_days=raw_chargeable_days,
            waived_days=waived_exam_days,
            net_chargeable_days=net_chargeable_days,
            base_demurrage=total_demurrage,
            capped_demurrage=total_demurrage,
            auction_fee=auction_fee,
            delisting_fee=delisting_fee,
            is_auction_listed=is_auction,
            is_capped=is_capped,
        )

