"""
Domain Model: Consignee / Shipper Party Entity.
"""
from dataclasses import dataclass


@dataclass
class Consignee:
    party_id: str
    party_name: str
    gstin: str
    city: str
