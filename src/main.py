"""
Main Application Entry Point.
Executes the command-file-driven Shipping Container Yard Allocation and Demurrage/Detention Billing Engine.
"""
import sys
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.config import (
    YARD_BLOCKS_CSV,
    TARIFF_CSV,
    FREE_DAYS_CSV,
    HOLIDAYS_CSV,
    SHIPPING_LINES_CSV,
    VESSELS_CSV,
    CONSIGNEES_CSV,
    CONTAINERS_CSV,
    COMMANDS_TXT,
    ALLOCATIONS_CSV,
    CONTAINER_LEDGER_CSV,
    YARD_OCCUPANCY_CSV,
    INVOICES_CSV,
)
from src.services.data_loader import DataLoader
from src.services.yard_allocator import YardAllocator
from src.services.free_days_service import FreeDaysService
from src.services.demurrage_service import DemurrageService
from src.services.detention_service import DetentionService
from src.services.reefer_service import ReeferService
from src.services.operations_service import OperationsService
from src.services.billing_service import BillingService
from src.services.command_processor import CommandProcessor
from src.services.report_generator import ReportGenerator
from src.validators.input_validator import InputValidator


def main():
    print("=" * 70)
    print("T090-PS-122: Container Yard Allocation & Billing Engine")
    print("Week 3 Capstone Implementation Runner")
    print("=" * 70)

    # 1. Load Data
    print("\n[Step 1] Loading master and operational datasets...")
    blocks = DataLoader.load_yard_blocks(YARD_BLOCKS_CSV)
    tariff = DataLoader.load_tariff(TARIFF_CSV)
    free_days_rules = DataLoader.load_free_days(FREE_DAYS_CSV)
    holidays = DataLoader.load_holidays(HOLIDAYS_CSV)
    shipping_lines = DataLoader.load_shipping_lines(SHIPPING_LINES_CSV)
    vessels = DataLoader.load_vessels(VESSELS_CSV)
    consignees = DataLoader.load_consignees(CONSIGNEES_CSV)
    containers_map = DataLoader.load_containers(CONTAINERS_CSV)
    
    # Preserve containers.csv file ordering for vessel discharge lists
    with open(CONTAINERS_CSV, "r", encoding="utf-8") as f:
        import csv
        reader = csv.DictReader(f)
        containers_ordered = [containers_map[row["container_no"].strip()] for row in reader]

    print(f"Loaded: {len(blocks)} yard blocks, {len(vessels)} vessels, {len(consignees)} parties, {len(containers_map)} containers.")

    # 2. Input Validation
    print("\n[Step 2] Performing comprehensive input validation...")
    validation_errors = []
    for c in containers_map.values():
        errs = InputValidator.validate_container(c, vessels)
        validation_errors.extend(errs)
    for b in blocks.values():
        errs = InputValidator.validate_yard_block(b)
        validation_errors.extend(errs)

    if validation_errors:
        print(f"Validation warnings found: {len(validation_errors)}")
        for e in validation_errors[:5]:
            print(f"  - {e}")
    else:
        print("All input data validated successfully with zero errors!")

    # 3. Initialize Services
    print("\n[Step 3] Initializing business rule services...")
    allocator = YardAllocator(blocks, containers_map)
    free_days_service = FreeDaysService(holidays, free_days_rules)
    demurrage_service = DemurrageService(tariff, free_days_service)
    detention_service = DetentionService(tariff)
    reefer_service = ReeferService(tariff)
    operations_service = OperationsService(tariff)
    billing_service = BillingService(
        tariff, demurrage_service, detention_service, reefer_service, operations_service
    )

    processor = CommandProcessor(
        containers=containers_map,
        containers_ordered_list=containers_ordered,
        blocks=blocks,
        vessels=vessels,
        tariff=tariff,
        allocator=allocator,
        demurrage_service=demurrage_service,
        detention_service=detention_service,
        reefer_service=reefer_service,
        operations_service=operations_service,
        billing_service=billing_service,
    )

    # 4. Process Commands Stream
    print(f"\n[Step 4] Processing event stream from {COMMANDS_TXT}...")
    processor.process_file(COMMANDS_TXT)
    print("Event stream processing completed successfully.")

    # 5. Generate Output Reports
    print("\n[Step 5] Writing official evaluation CSV reports...")
    ReportGenerator.write_allocations(processor.allocations_records, ALLOCATIONS_CSV)
    ReportGenerator.write_container_ledger(processor.ledger_records, CONTAINER_LEDGER_CSV)
    ReportGenerator.write_yard_occupancy(processor.yard_occupancy_records, YARD_OCCUPANCY_CSV)
    ReportGenerator.write_invoices(processor.invoices_records, INVOICES_CSV)

    print(f"Generated: {ALLOCATIONS_CSV} ({len(processor.allocations_records)} rows)")
    print(f"Generated: {CONTAINER_LEDGER_CSV} ({len(processor.ledger_records)} rows)")
    print(f"Generated: {YARD_OCCUPANCY_CSV} ({len(processor.yard_occupancy_records)} rows)")
    print(f"Generated: {INVOICES_CSV} ({len(processor.invoices_records)} rows)")
    print("\n" + "=" * 70)
    print("Execution completed successfully!")
    print("=" * 70)


if __name__ == "__main__":
    main()

