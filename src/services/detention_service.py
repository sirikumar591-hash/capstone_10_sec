"""
Service: Detention Calculation.
Implements BR-05: Post-Gate-Out Detention Calculation and 7-day Free Period.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Tuple
from src.models.container import Container
from src.models.tariff import TariffTable
from src.utils.constants import ChargeCode
from src.utils.money_utils import round_money, to_decimal


@dataclass
class DetentionResult:
    total_days_out: int
    chargeable_days: int
    detention_amount: Decimal


class DetentionService:
    def __init__(self, tariff: TariffTable):
        self.tariff = tariff

    def calculate_detention(
        self,
        container: Container,
        as_of_dt: datetime,
    ) -> DetentionResult:
        """
        Calculates detention equipment retention charges.
        BR-05:
        - 7 free days from gate-out.
        - Days 8-14: 20-ft = 1500.00, 40-ft = 2800.00.
        - Day 15+: Doubled.
        - Stops at empty return gate-in timestamp.
        """
        if not container.gate_out_ts:
            return DetentionResult(0, 0, Decimal("0.00"))

        end_dt = container.empty_return_ts if container.empty_return_ts else as_of_dt
        if end_dt < container.gate_out_ts:
            return DetentionResult(0, 0, Decimal("0.00"))

        # Elapsed days outside terminal
        elapsed_days = (end_dt.date() - container.gate_out_ts.date()).days
        # If return has occurred on the 7th day within 7 x 24h, it is within the 7 free days
        if elapsed_days <= 7:
            return DetentionResult(elapsed_days, 0, Decimal("0.00"))

        chargeable_days = elapsed_days - 7
        total_amount = Decimal("0.00")

        for day in range(8, elapsed_days + 1):
            rate = self.tariff.get_detention_rate(day, container.size_ft)
            total_amount += rate

        return DetentionResult(
            total_days_out=elapsed_days,
            chargeable_days=chargeable_days,
            detention_amount=round_money(total_amount),
        )

