"""
Domain Model: Invoice and Invoice Line Entities.
Represents billed amounts per consignee per vessel, including GST and interest.
"""
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import List, Optional
from src.utils.constants import ChargeCode
from src.utils.money_utils import round_money, to_decimal


@dataclass
class InvoiceLine:
    invoice_id: str
    party_id: str
    vessel_id: str
    issue_date: str
    container_no: str
    charge_code: str
    amount: Decimal


@dataclass
class Invoice:
    invoice_id: str
    party_id: str
    vessel_id: str
    issue_date: date
    lines: List[InvoiceLine] = field(default_factory=list)
    paid: bool = False
    paid_date: Optional[date] = None

    @property
    def subtotal(self) -> Decimal:
        """Sum of all itemized container charge lines."""
        return sum((line.amount for line in self.lines), Decimal("0.00"))

    @property
    def gst_amount(self) -> Decimal:
        """18% GST on subtotal."""
        return round_money(self.subtotal * Decimal("0.18"))

    @property
    def total_with_gst(self) -> Decimal:
        """Subtotal + GST."""
        return self.subtotal + self.gst_amount

    def calculate_interest(self, as_of_date: Optional[date] = None) -> Decimal:
        """
        Calculates late payment interest (1.5% per month).
        Applies if unpaid 15 days after issue date.
        """
        eval_date = self.paid_date if self.paid else as_of_date
        if not eval_date:
            return Decimal("0.00")

        days_elapsed = (eval_date - self.issue_date).days
        if days_elapsed > 15:
            # 1.5% interest on total invoice amount (or subtotal)
            return round_money(self.total_with_gst * Decimal("0.015"))
        return Decimal("0.00")
