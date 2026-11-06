"""
Service: Data Loader.
Loads, validates, and parses all CSV data files into domain models.
"""
import csv
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Set, Tuple

from src.models.consignee import Consignee
from src.models.container import Container
from src.models.tariff import TariffItem, TariffTable
from src.models.vessel import Vessel
from src.models.yard_block import YardBlock
from src.utils.constants import ContainerType, Direction
from src.utils.date_utils import parse_date, parse_datetime
from src.utils.money_utils import to_decimal


class DataLoader:
    @staticmethod
    def load_yard_blocks(path: Path) -> Dict[str, YardBlock]:
        blocks = {}
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                block_id = row["block_id"].strip()
                block = YardBlock(
                    block_id=block_id,
                    block_type=ContainerType(row["block_type"].strip()),
                    rows=int(row["rows"]),
                    bays_per_row=int(row["bays_per_row"]),
                    max_tiers=int(row["max_tiers"]),
                    capacity_teu=int(row["capacity_teu"]),
                    plug_points=int(row["plug_points"]),
                )
                blocks[block_id] = block
        return blocks

    @staticmethod
    def load_tariff(path: Path) -> TariffTable:
        items = []
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                size_ft = int(row["size_ft"].strip()) if row.get("size_ft") and row["size_ft"].strip() else None
                slab_from = int(row["slab_from_day"].strip()) if row.get("slab_from_day") and row["slab_from_day"].strip() else None
                slab_to = int(row["slab_to_day"].strip()) if row.get("slab_to_day") and row["slab_to_day"].strip() else None
                rate = to_decimal(row["rate"].strip()) if row.get("rate") and row["rate"].strip() else Decimal("0.00")
                item = TariffItem(
                    charge_code=row["charge_code"].strip(),
                    size_ft=size_ft,
                    slab_from_day=slab_from,
                    slab_to_day=slab_to,
                    rate=rate,
                    unit=row["unit"].strip() if row.get("unit") else "",
                    notes=row.get("notes", "").strip(),
                )
                items.append(item)
        return TariffTable(items)

    @staticmethod
    def load_free_days(path: Path) -> Dict[Tuple[str, str], int]:
        """Maps (movement, container_type) -> free_days."""
        free_days_map = {}
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                m = row["movement"].strip()
                t = row["container_type"].strip()
                days = int(row["free_days"].strip())
                free_days_map[(m, t)] = days
        return free_days_map

    @staticmethod
    def load_holidays(path: Path) -> Set[date]:
        holidays = set()
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                holidays.add(parse_date(row["holiday_date"]))
        return holidays

    @staticmethod
    def load_shipping_lines(path: Path) -> Dict[str, Dict[str, str]]:
        lines = {}
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                code = row["line_code"].strip()
                lines[code] = {
                    "line_code": code,
                    "line_name": row["line_name"].strip(),
                    "owner_prefix": row["owner_prefix"].strip(),
                }
        return lines

    @staticmethod
    def load_vessels(path: Path) -> Dict[str, Vessel]:
        vessels = {}
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                v_id = row["vessel_id"].strip()
                vessel = Vessel(
                    vessel_id=v_id,
                    vessel_name=row["vessel_name"].strip(),
                    voyage_no=row["voyage_no"].strip(),
                    line_code=row["line_code"].strip(),
                    eta=parse_datetime(row["eta"]),
                    etd=parse_datetime(row["etd"]),
                    export_cutoff=parse_datetime(row["export_cutoff"]),
                )
                vessels[v_id] = vessel
        return vessels

    @staticmethod
    def load_consignees(path: Path) -> Dict[str, Consignee]:
        consignees = {}
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                p_id = row["party_id"].strip()
                consignees[p_id] = Consignee(
                    party_id=p_id,
                    party_name=row["party_name"].strip(),
                    gstin=row["gstin"].strip(),
                    city=row["city"].strip(),
                )
        return consignees

    @staticmethod
    def load_containers(path: Path) -> Dict[str, Container]:
        containers = {}
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                c_no = row["container_no"].strip()
                imo = row.get("imo_class", "").strip() or None
                set_temp = to_decimal(row["set_temp_c"].strip()) if row.get("set_temp_c") and row["set_temp_c"].strip() else None
                container = Container(
                    container_no=c_no,
                    size_ft=int(row["size_ft"].strip()),
                    container_type=ContainerType(row["container_type"].strip()),
                    gross_weight_t=to_decimal(row["gross_weight_t"].strip()),
                    direction=Direction(row["direction"].strip()),
                    vessel_id=row["vessel_id"].strip(),
                    line_code=row["line_code"].strip(),
                    destination=row["destination"].strip(),
                    party_id=row["party_id"].strip(),
                    imo_class=imo,
                    set_temp_c=set_temp,
                )
                containers[c_no] = container
        return containers
