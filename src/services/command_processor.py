"""
Service: Command File Processor.
Processes sequential command events from commands.txt and orchestrates domain services.
"""
from datetime import datetime, date
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from src.models.container import Container
from src.models.invoice import Invoice
from src.models.tariff import TariffTable
from src.models.vessel import Vessel
from src.models.yard_block import YardBlock
from src.services.billing_service import BillingService
from src.services.demurrage_service import DemurrageService
from src.services.detention_service import DetentionService
from src.services.gate_service import GateService
from src.services.operations_service import OperationsService
from src.services.reefer_service import ReeferService
from src.services.yard_allocator import YardAllocator
from src.utils.constants import ChargeCode, ContainerState, ContainerType, Direction, Flag, RestowReason, ShutOutReason
from src.utils.date_utils import format_date, format_datetime, parse_date, parse_datetime
from src.utils.money_utils import format_money, round_money, to_decimal


class CommandProcessor:
    def __init__(
        self,
        containers: Dict[str, Container],
        containers_ordered_list: List[Container],
        blocks: Dict[str, YardBlock],
        vessels: Dict[str, Vessel],
        tariff: TariffTable,
        allocator: YardAllocator,
        demurrage_service: DemurrageService,
        detention_service: DetentionService,
        reefer_service: ReeferService,
        operations_service: OperationsService,
        billing_service: BillingService,
    ):
        self.containers = containers
        self.containers_ordered_list = containers_ordered_list
        self.blocks = blocks
        self.vessels = vessels
        self.tariff = tariff
        self.allocator = allocator
        self.demurrage_service = demurrage_service
        self.detention_service = detention_service
        self.reefer_service = reefer_service
        self.operations_service = operations_service
        self.billing_service = billing_service

        # Output collection records
        self.allocations_records: List[Dict[str, str]] = []
        self.ledger_records: List[Dict[str, str]] = []
        self.yard_occupancy_records: List[Dict[str, str]] = []
        self.invoices_records: List[Dict[str, str]] = []

    def record_allocation(self, container_no: str, ts: datetime, block_id: str, row: int, bay: int, tier: int, reason: str):
        self.allocations_records.append({
            "container_no": container_no,
            "ts": format_datetime(ts),
            "block_id": block_id,
            "row": str(row),
            "bay": str(bay),
            "tier": str(tier),
            "reason": reason,
        })

    def record_ledger_state(self, container: Container, dt: datetime, state: ContainerState):
        flags_str = " ".join(sorted(container.flags)) if container.flags else ""
        self.ledger_records.append({
            "container_no": container.container_no,
            "line_date": format_date(dt.date()),
            "state": state.value,
            "charge_code": "",
            "days": "",
            "rate": "",
            "amount": "",
            "bill_to": "",
            "flags": flags_str,
        })

    def record_ledger_charge(
        self,
        container: Container,
        dt: datetime,
        charge_code: str,
        days: int,
        rate: Decimal,
        amount: Decimal,
        bill_to: str,
    ):
        flags_str = " ".join(sorted(container.flags)) if container.flags else ""
        self.ledger_records.append({
            "container_no": container.container_no,
            "line_date": format_date(dt.date()),
            "state": container.state.value if container.state else "",
            "charge_code": charge_code,
            "days": str(days) if days > 0 else "",
            "rate": format_money(rate),
            "amount": format_money(amount),
            "bill_to": bill_to,
            "flags": flags_str,
        })

    def process_file(self, commands_path: Path):
        """Processes commands.txt line by line in strict file order."""
        with open(commands_path, "r", encoding="utf-8") as f:
            for line_no, raw_line in enumerate(f, 1):
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue

                parts = [p.strip() for p in line.split("|")]
                cmd = parts[0]

                try:
                    self.execute_command(cmd, parts[1:], line_no)
                except Exception as e:
                    print(f"Error on line {line_no} ({line}): {e}")

    def execute_command(self, cmd: str, args: List[str], line_no: int):
        if cmd == "DISCHARGE_COMPLETE":
            vessel_id = args[0]
            ts = parse_datetime(args[1])
            # Allocate all import containers belonging to this vessel in containers.csv file order
            for c in self.containers_ordered_list:
                if c.direction == Direction.IMPORT and c.vessel_id == vessel_id:
                    c.discharge_ts = ts
                    c.state = ContainerState.DISCHARGED
                    self.record_ledger_state(c, ts, ContainerState.DISCHARGED)
                    
                    block_id, row, bay, tier = self.allocator.allocate_container(c, reason="DISCHARGE")
                    c.state = ContainerState.YARD
                    self.record_allocation(c.container_no, ts, block_id, row, bay, tier, "DISCHARGE")
                    self.record_ledger_state(c, ts, ContainerState.YARD)

        elif cmd == "GATE_IN":
            c_no = args[0]
            ts = parse_datetime(args[1])
            c = self.containers.get(c_no)
            if c:
                c.gate_in_ts = ts
                c.state = ContainerState.YARD
                block_id, row, bay, tier = self.allocator.allocate_container(c, reason="GATE_IN")
                self.record_allocation(c.container_no, ts, block_id, row, bay, tier, "GATE_IN")
                self.record_ledger_state(c, ts, ContainerState.YARD)

        elif cmd == "GATE_OUT":
            c_no = args[0]
            ts = parse_datetime(args[1])
            customs_ooc = args[2]
            delivery_order = args[3]
            payment_receipt = args[4]

            c = self.containers.get(c_no)
            if c:
                is_valid, err = GateService.validate_gate_out(c, ts, customs_ooc, delivery_order, payment_receipt)
                if not is_valid:
                    # Gate-out refused (hold check failed)
                    # print(f"GATE_OUT Refused for {c_no}: {err}")
                    pass
                else:
                    self.allocator.deallocate_container(c)
                    c.gate_out_ts = ts
                    c.state = ContainerState.GATE_OUT
                    self.record_ledger_state(c, ts, ContainerState.GATE_OUT)

        elif cmd == "EMPTY_RETURN":
            c_no = args[0]
            ts = parse_datetime(args[1])
            c = self.containers.get(c_no)
            if c:
                c.empty_return_ts = ts
                c.state = ContainerState.EMPTY_RETURNED
                # Allocate to an EMPTY block
                # Create empty container representation
                c.container_type = ContainerType.EMPTY
                block_id, row, bay, tier = self.allocator.allocate_container(c, reason="EMPTY_RETURN")
                self.record_allocation(c.container_no, ts, block_id, row, bay, tier, "EMPTY_RETURN")
                self.record_ledger_state(c, ts, ContainerState.EMPTY_RETURNED)

        elif cmd == "EXAM_START":
            c_no = args[0]
            ts = parse_datetime(args[1])
            c = self.containers.get(c_no)
            if c:
                c.exam_start_ts = ts

        elif cmd == "EXAM_END":
            c_no = args[0]
            ts = parse_datetime(args[1])
            c = self.containers.get(c_no)
            if c:
                c.exam_end_ts = ts

        elif cmd == "RESTOW":
            c_no = args[0]
            ts = parse_datetime(args[1])
            reason = args[2]
            to_block = args[3]

            c = self.containers.get(c_no)
            if c:
                charge_amt, bill_to = self.operations_service.process_restow(c, ts, reason)
                c.state = ContainerState.RESTOWED
                self.record_ledger_state(c, ts, ContainerState.RESTOWED)
                self.record_ledger_charge(
                    c, ts, ChargeCode.LIFT.value, 1, charge_amt, charge_amt, bill_to
                )
                
                # Reallocate
                self.allocator.deallocate_container(c)
                target_block = to_block if to_block != "-" else None
                if target_block and target_block in self.blocks:
                    block = self.blocks[target_block]
                    slot = block.find_first_available_slot(c.size_ft, c.is_overweight)
                    if slot:
                        row, bay, tier = slot
                        block.allocate(c.container_no, c.size_ft, row, bay, tier)
                        c.current_block = block.block_id
                        c.current_row = row
                        c.current_bay = bay
                        c.current_tier = tier
                        b_id, r, b, t = (block.block_id, row, bay, tier)
                    else:
                        b_id, r, b, t = self.allocator.allocate_container(c, reason="RESTOW")
                else:
                    b_id, r, b, t = self.allocator.allocate_container(c, reason="RESTOW")

                c.state = ContainerState.YARD
                self.record_allocation(c.container_no, ts, b_id, r, b, t, "RESTOW")
                self.record_ledger_state(c, ts, ContainerState.YARD)

        elif cmd == "SHUT_OUT":
            c_no = args[0]
            ts = parse_datetime(args[1])
            reason = args[2]
            c = self.containers.get(c_no)
            if c:
                fee, reason_enum = self.operations_service.process_shut_out(c, ts, reason)
                c.state = ContainerState.SHUT_OUT
                self.record_ledger_state(c, ts, ContainerState.SHUT_OUT)
                if fee > Decimal("0.00"):
                    self.record_ledger_charge(
                        c, ts, ChargeCode.SHUT_OUT.value, 1, fee, fee, c.party_id
                    )

        elif cmd == "LOAD":
            c_no = args[0]
            v_id = args[1]
            ts = parse_datetime(args[2])
            c = self.containers.get(c_no)
            if c:
                self.allocator.deallocate_container(c)
                c.load_ts = ts
                c.state = ContainerState.LOADED
                self.record_ledger_state(c, ts, ContainerState.LOADED)

        elif cmd == "TEMP_DEVIATION":
            c_no = args[0]
            start_ts = parse_datetime(args[1])
            end_ts = parse_datetime(args[2])
            temp_c = to_decimal(args[3])
            c = self.containers.get(c_no)
            if c:
                self.reefer_service.process_temperature_deviation(c, start_ts, end_ts, temp_c)

        elif cmd == "MANAGER_APPROVE":
            c_no = args[0]
            app_date = parse_date(args[1])
            c = self.containers.get(c_no)
            if c:
                c.manager_approved = True
                c.manager_approve_date = app_date

        elif cmd == "ISSUE_INVOICE":
            party_id = args[0]
            vessel_id = args[1]
            issue_date = parse_date(args[2])
            inv, err = self.billing_service.issue_invoice(
                party_id, vessel_id, issue_date, list(self.containers.values())
            )
            # if err:
            #     print(f"Invoice Issue Warning for {party_id}-{vessel_id}: {err}")

        elif cmd == "INVOICE_PAYMENT":
            party_id = args[0]
            vessel_id = args[1]
            pay_date = parse_date(args[2])
            self.billing_service.record_payment(party_id, vessel_id, pay_date)

        elif cmd == "PRINT_YARD_OCCUPANCY":
            report_date = parse_date(args[0])
            for b_id in sorted(self.blocks.keys()):
                block = self.blocks[b_id]
                self.yard_occupancy_records.append({
                    "date": format_date(report_date),
                    "block_id": block.block_id,
                    "teu_used": str(block.teu_used),
                    "capacity_teu": str(block.capacity_teu),
                    "occupancy_pct": f"{block.occupancy_pct:.2f}",
                    "containers": str(len(block.containers)),
                })

        elif cmd == "PRINT_INVOICE":
            party_id = args[0]
            vessel_id = args[1]
            key = (party_id, vessel_id)
            if key in self.billing_service.invoices:
                inv = self.billing_service.invoices[key]
                # Emit invoice lines
                for line in inv.lines:
                    self.invoices_records.append({
                        "invoice_id": inv.invoice_id,
                        "party_id": inv.party_id,
                        "vessel_id": inv.vessel_id,
                        "issue_date": str(inv.issue_date),
                        "container_no": line.container_no,
                        "charge_code": line.charge_code,
                        "amount": format_money(line.amount),
                    })
                # Emit TOTAL line
                self.invoices_records.append({
                    "invoice_id": inv.invoice_id,
                    "party_id": inv.party_id,
                    "vessel_id": inv.vessel_id,
                    "issue_date": str(inv.issue_date),
                    "container_no": "",
                    "charge_code": ChargeCode.TOTAL.value,
                    "amount": format_money(inv.subtotal),
                })
                # Emit GST line
                self.invoices_records.append({
                    "invoice_id": inv.invoice_id,
                    "party_id": inv.party_id,
                    "vessel_id": inv.vessel_id,
                    "issue_date": str(inv.issue_date),
                    "container_no": "",
                    "charge_code": ChargeCode.GST.value,
                    "amount": format_money(inv.gst_amount),
                })
                # Emit INTEREST line
                interest_amt = inv.calculate_interest(as_of_date=date(2026, 9, 29))
                self.invoices_records.append({
                    "invoice_id": inv.invoice_id,
                    "party_id": inv.party_id,
                    "vessel_id": inv.vessel_id,
                    "issue_date": str(inv.issue_date),
                    "container_no": "",
                    "charge_code": ChargeCode.INTEREST.value,
                    "amount": format_money(interest_amt),
                })

        elif cmd == "PRINT_LEDGER":
            c_no = args[0]
            as_of_date = parse_date(args[1])
            c = self.containers.get(c_no)
            if c:
                # Add calculated demurrage, detention, and plug-in charge lines as of date if applicable
                as_of_dt = datetime.combine(as_of_date, datetime.max.time().replace(microsecond=0))
                # Demurrage
                dem_res = self.demurrage_service.calculate_demurrage(c, as_of_dt)
                if dem_res.capped_demurrage > Decimal("0.00"):
                    self.record_ledger_charge(
                        c, as_of_dt, ChargeCode.DEMURRAGE_DRY.value,
                        dem_res.net_chargeable_days,
                        round_money(dem_res.capped_demurrage / dem_res.net_chargeable_days) if dem_res.net_chargeable_days > 0 else Decimal("0.00"),
                        dem_res.capped_demurrage,
                        c.party_id,
                    )
                # Reefer plug-in
                plug_amt = self.reefer_service.calculate_plugin_charge(c, as_of_dt)
                if plug_amt > Decimal("0.00"):
                    self.record_ledger_charge(
                        c, as_of_dt, ChargeCode.REEFER_PLUG.value,
                        0, self.tariff.get_flat_rate(ChargeCode.REEFER_PLUG.value),
                        plug_amt, c.party_id,
                    )
                # Detention
                det_res = self.detention_service.calculate_detention(c, as_of_dt)
                if det_res.detention_amount > Decimal("0.00"):
                    self.record_ledger_charge(
                        c, as_of_dt, ChargeCode.DETENTION.value,
                        det_res.chargeable_days,
                        round_money(det_res.detention_amount / det_res.chargeable_days) if det_res.chargeable_days > 0 else Decimal("0.00"),
                        det_res.detention_amount,
                        c.party_id,
                    )

