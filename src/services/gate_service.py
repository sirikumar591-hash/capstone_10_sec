"""
Service: Gate Operations & Hold Validation.
Implements BR-06: Gate-out Hold Checks (Customs OOC, Delivery Order, Terminal Payment, Active Exam).
"""
from datetime import datetime
from typing import Optional, Tuple
from src.models.container import Container
from src.utils.constants import ContainerState


class GateService:
    @staticmethod
    def validate_gate_out(
        container: Container,
        ts: datetime,
        customs_ooc: str,
        delivery_order: str,
        payment_receipt: str,
    ) -> Tuple[bool, Optional[str]]:
        """
        Validates all gate-out hold requirements (BR-06):
        1. Customs Out of Charge (OOC) flag must be true.
        2. Delivery Order must be true.
        3. Terminal charges must be paid (valid payment receipt).
        4. Container must not be under active examination.
        Returns (is_valid, error_reason).
        """
        # Active customs examination check
        if container.exam_start_ts and not container.exam_end_ts:
            return False, "Container is under active customs examination"
        if container.exam_start_ts and container.exam_end_ts:
            if container.exam_start_ts <= ts < container.exam_end_ts:
                return False, "Container is under active customs examination"

        # Customs OOC check
        if str(customs_ooc).strip().lower() != "true":
            return False, "Customs Out of Charge (OOC) flag is missing or false"

        # Delivery order check
        if str(delivery_order).strip().lower() != "true":
            return False, "Shipping line Delivery Order is missing or false"

        # Payment receipt check
        p = str(payment_receipt).strip()
        if not p or p == "-":
            return False, "Terminal charges have not been paid in full (missing payment receipt)"

        return True, None

