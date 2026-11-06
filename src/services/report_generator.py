"""
Service: Report Generator.
Writes out official evaluation CSV reports in exact format specified by README.md.
"""
import csv
from pathlib import Path
from typing import Dict, List


class ReportGenerator:
    @staticmethod
    def write_allocations(records: List[Dict[str, str]], output_path: Path):
        fieldnames = ["container_no", "ts", "block_id", "row", "bay", "tier", "reason"]
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in records:
                writer.writerow(r)

    @staticmethod
    def write_container_ledger(records: List[Dict[str, str]], output_path: Path):
        fieldnames = ["container_no", "line_date", "state", "charge_code", "days", "rate", "amount", "bill_to", "flags"]
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in records:
                writer.writerow(r)

    @staticmethod
    def write_yard_occupancy(records: List[Dict[str, str]], output_path: Path):
        fieldnames = ["date", "block_id", "teu_used", "capacity_teu", "occupancy_pct", "containers"]
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in records:
                writer.writerow(r)

    @staticmethod
    def write_invoices(records: List[Dict[str, str]], output_path: Path):
        fieldnames = ["invoice_id", "party_id", "vessel_id", "issue_date", "container_no", "charge_code", "amount"]
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in records:
                writer.writerow(r)

