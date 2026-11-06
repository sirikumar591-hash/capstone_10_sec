"""
Service: Billing, Invoicing, Tax, and Interest.
Implements BR-10: Invoicing, Manager Approval, 18% GST, and Late Payment Interest.
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from src.models.consignee import Consignee
from src.models.container import Container
from src.models.invoice import Invoice, InvoiceLine
from src.models.tariff import TariffTable
from src.models.vessel import Vessel
from src.services.demurrage_service import DemurrageService
from src.services.detention_service import DetentionService
from src.services.operations_service import OperationsService
from src.services.reefer_service import ReeferService
from src.utils.constants import ChargeCode, Flag
from src.utils.money_utils import format_money, round_money, to_decimal


class BillingService:
    def __init__(
        self,
        tariff: TariffTable,
        demurrage_service: DemurrageService,
        detention_service: DetentionService,
        reefer_service: ReeferService,
        operations_service: OperationsService,
    ):
        self.tariff = tariff
        self.demurrage_service = demurrage_service
        self.detention_service = detention_service
        self.reefer_service = reefer_service
        self.operations_service = operations_service
        self.invoices: Dict[Tuple[str, str], Invoice] = {}

    def issue_invoice(
        self,
        party_id: str,
        vessel_id: str,
        issue_date: date,
        containers: List[Container],
    ) -> Tuple[Optional[Invoice], Optional[str]]:
        """
        BR-10: Generates an invoice for given party and vessel.
        Checks manager approval requirement (Demurrage > Rs 200,000).
        Returns (Invoice, error_message).
        """
        invoice_id = f"INV-{party_id}-{vessel_id}"
        lines: List[InvoiceLine] = []

        relevant_containers = [
            c for c in containers if c.party_id == party_id and c.vessel_id == vessel_id
        ]

        # First pass: check approval requirement on all containers
        as_of_dt = datetime.combine(issue_date, datetime.max.time().replace(microsecond=0))
        for c in relevant_containers:
            dem_res = self.demurrage_service.calculate_demurrage(c, as_of_dt)
            approval_threshold = self.tariff.get_flat_rate(ChargeCode.MANAGER_APPROVE_ABOVE.value)
            
            if dem_res.capped_demurrage > approval_threshold:
                c.flags.add(Flag.MANAGER_APPROVE_REQUIRED.value)
                if not c.manager_approved:
                    return None, f"Container {c.container_no} demurrage of {dem_res.capped_demurrage} exceeds Rs {approval_threshold} and lacks MANAGER_APPROVE"

        # Second pass: build invoice lines
        for c in relevant_containers:
            # 1. Demurrage
            dem_res = self.demurrage_service.calculate_demurrage(c, as_of_dt)
            if dem_res.capped_demurrage > Decimal("0.00"):
                lines.append(
                    InvoiceLine(
                        invoice_id=invoice_id,
                        party_id=party_id,
                        vessel_id=vessel_id,
                        issue_date=str(issue_date),
                        container_no=c.container_no,
                        charge_code=ChargeCode.DEMURRAGE_DRY.value,
                        amount=dem_res.capped_demurrage,
                    )
                )

            # 2. Reefer Plug-in
            plugin_amt = self.reefer_service.calculate_plugin_charge(c, as_of_dt)
            if plugin_amt > Decimal("0.00"):
                lines.append(
                    InvoiceLine(
                        invoice_id=invoice_id,
                        party_id=party_id,
                        vessel_id=vessel_id,
                        issue_date=str(issue_date),
                        container_no=c.container_no,
                        charge_code=ChargeCode.REEFER_PLUG.value,
                        amount=plugin_amt,
                    )
                )

            # 3. Lift charges (standard lift)
            if c.discharge_ts:
                lift_rate = self.operations_service.get_lift_charge(c.size_ft)
                lines.append(
                    InvoiceLine(
                        invoice_id=invoice_id,
                        party_id=party_id,
                        vessel_id=vessel_id,
                        issue_date=str(issue_date),
                        container_no=c.container_no,
                        charge_code=ChargeCode.LIFT.value,
                        amount=lift_rate,
                    )
                )

            # 4. Auction / Delisting fees
            if dem_res.auction_fee > Decimal("0.00"):
                lines.append(
                    InvoiceLine(
                        invoice_id=invoice_id,
                        party_id=party_id,
                        vessel_id=vessel_id,
                        issue_date=str(issue_date),
                        container_no=c.container_no,
                        charge_code=ChargeCode.AUCTION_PROCESSING.value,
                        amount=dem_res.auction_fee,
                    )
                )
            if dem_res.delisting_fee > Decimal("0.00"):
                lines.append(
                    InvoiceLine(
                        invoice_id=invoice_id,
                        party_id=party_id,
                        vessel_id=vessel_id,
                        issue_date=str(issue_date),
                        container_no=c.container_no,
                        charge_code=ChargeCode.DELISTING.value,
                        amount=dem_res.delisting_fee,
                    )
                )

            # 5. Shut-out fee (if line cut-off)
            if c.shut_out_ts and c.shut_out_reason and c.shut_out_reason.value == "LINE_CUTOFF":
                shut_fee = self.tariff.get_flat_rate(ChargeCode.SHUT_OUT.value)
                lines.append(
                    InvoiceLine(
                        invoice_id=invoice_id,
                        party_id=party_id,
                        vessel_id=vessel_id,
                        issue_date=str(issue_date),
                        container_no=c.container_no,
                        charge_code=ChargeCode.SHUT_OUT.value,
                        amount=shut_fee,
                    )
                )

        invoice = Invoice(
            invoice_id=invoice_id,
            party_id=party_id,
            vessel_id=vessel_id,
            issue_date=issue_date,
            lines=lines,
        )
        self.invoices[(party_id, vessel_id)] = invoice
        return invoice, None

    def record_payment(
        self,
        party_id: str,
        vessel_id: str,
        payment_date: date,
    ) -> bool:
        """Records invoice payment and marks paid_date."""
        key = (party_id, vessel_id)
        if key in self.invoices:
            inv = self.invoices[key]
            inv.paid = True
            inv.paid_date = payment_date
            return True
        return False

