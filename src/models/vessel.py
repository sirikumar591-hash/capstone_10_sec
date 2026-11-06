"""
Domain Model: Vessel Entity.
Represents vessel call with ETA, ETD, line ownership, and export cutoff.
"""
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Vessel:
    vessel_id: str
    vessel_name: str
    voyage_no: str
    line_code: str
    eta: datetime
    etd: datetime
    export_cutoff: datetime
