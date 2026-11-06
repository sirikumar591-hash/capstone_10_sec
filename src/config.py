"""
Configuration and File Paths for the Logistics Engine.
"""
from pathlib import Path

# Base directory is project root
BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"
OUTPUTS_DIR = BASE_DIR / "outputs"

# Input file paths
YARD_BLOCKS_CSV = DATA_DIR / "yard_blocks.csv"
TARIFF_CSV = DATA_DIR / "tariff.csv"
FREE_DAYS_CSV = DATA_DIR / "free_days.csv"
HOLIDAYS_CSV = DATA_DIR / "holidays.csv"
SHIPPING_LINES_CSV = DATA_DIR / "shipping_lines.csv"
VESSELS_CSV = DATA_DIR / "vessels.csv"
CONSIGNEES_CSV = DATA_DIR / "consignees.csv"
CONTAINERS_CSV = DATA_DIR / "containers.csv"
COMMANDS_TXT = DATA_DIR / "commands.txt"

# Output file paths
ALLOCATIONS_CSV = OUTPUTS_DIR / "allocations.csv"
CONTAINER_LEDGER_CSV = OUTPUTS_DIR / "container_ledger.csv"
YARD_OCCUPANCY_CSV = OUTPUTS_DIR / "yard_occupancy.csv"
INVOICES_CSV = OUTPUTS_DIR / "invoices.csv"
