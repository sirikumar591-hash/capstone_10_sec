"""
Service: Terminal Operations (Lifts, Restows, Shut-Outs).
Implements BR-07 (Lift & Restow Attribution) and BR-08 (Export Shut-Out Rules).
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional, Tuple
from src.models.container import Container
from src.models.tariff import TariffTable
from src.utils.constants import ChargeCode, RestowReason, ShutOutReason
from src.utils.money_utils import to_decimal


class OperationsService:
    def __init__(self, tariff: TariffTable):
        self.tariff = tariff

    def get_lift_charge(self, size_ft: int) -> Decimal:
        """BR-07: Lift charge: 20-ft = 3000.00, 40-ft = 4500.00."""
        return self.tariff.get_flat_rate(ChargeCode.LIFT.value, size_ft)

    def process_restow(
        self,
        container: Container,
        ts: datetime,
        reason: str,
    ) -> Tuple[Decimal, str]:
        """
        BR-07: Restow processing.
        Returns (charge_amount, bill_to).
        - If CONSIGNEE_REQUEST: billed to container.party_id.
        - If TERMINAL_ACCESS: billed to TERMINAL.
        """
        container.restow_count += 1
        lift_fee = self.get_lift_charge(container.size_ft)
        
        reason_upper = reason.strip().upper()
        if reason_upper == RestowReason.CONSIGNEE_REQUEST.value:
            return lift_fee, container.party_id
        else:
            return lift_fee, "TERMINAL"

    def process_shut_out(
        self,
        container: Container,
        ts: datetime,
        reason: str,
    ) -> Tuple[Decimal, ShutOutReason]:
        """
        BR-08: Shut-Out processing.
        Returns (shut_out_fee, reason_enum).
        - LINE_CUTOFF: 5000.00 fee, storage restarts with 2 free days.
        - YARD_CONGESTION: 0.00 fee, storage restarts with 2 free days.
        """
        container.shut_out_ts = ts
        reason_upper = reason.strip().upper()
        if reason_upper == ShutOutReason.LINE_CUTOFF.value:
            container.shut_out_reason = ShutOutReason.LINE_CUTOFF
            fee = self.tariff.get_flat_rate(ChargeCode.SHUT_OUT.value)
            return fee, ShutOutReason.LINE_CUTOFF
        else:
            container.shut_out_reason = ShutOutReason.YARD_CONGESTION
            return Decimal("0.00"), ShutOutReason.YARD_CONGESTION

