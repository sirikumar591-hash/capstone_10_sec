"""
Domain Model: Tariff Entity and Tariff Table.
Maintains rates, slab thresholds, multipliers, fees, GST, and interest rates.
"""
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional, List
from src.utils.constants import ChargeCode
from src.utils.money_utils import to_decimal


@dataclass
class TariffItem:
    charge_code: str
    rate: Decimal
    unit: str
    size_ft: Optional[int] = None
    slab_from_day: Optional[int] = None
    slab_to_day: Optional[int] = None
    notes: Optional[str] = None


class TariffTable:
    def __init__(self, items: List[TariffItem]):
        self.items = items

    def get_demurrage_rate(self, day_number: int, size_ft: int) -> Decimal:
        """
        Determines base 20-ft demurrage rate for given day number, then applies 40-ft multiplier if applicable.
        BR-04:
        Days 1-5: 1200.00
        Days 6-10: 2000.00
        Days 11+: 3500.00
        40-ft size multiplier = 1.6
        """
        base_rate = Decimal("0.00")
        for item in self.items:
            if item.charge_code == ChargeCode.DEMURRAGE_DRY and (item.size_ft == 20 or item.size_ft is None):
                from_day = item.slab_from_day or 1
                to_day = item.slab_to_day or 999999
                if from_day <= day_number <= to_day:
                    base_rate = item.rate
                    break

        if size_ft == 40:
            mult = self.get_multiplier(ChargeCode.SIZE_MULT_40, Decimal("1.60"))
            return base_rate * mult
        return base_rate

    def get_detention_rate(self, day_number: int, size_ft: int) -> Decimal:
        """
        Determines daily detention rate.
        BR-05:
        Days 1-7: Free (0.00)
        Days 8-14: 20-ft = 1500.00, 40-ft = 2800.00
        Days 15+: Doubled (3000.00 / 5600.00)
        """
        if day_number <= 7:
            return Decimal("0.00")

        base_rate = Decimal("0.00")
        for item in self.items:
            if item.charge_code == ChargeCode.DETENTION and item.size_ft == size_ft:
                base_rate = item.rate
                break

        if day_number >= 15:
            return base_rate * Decimal("2.00")
        return base_rate

    def get_multiplier(self, charge_code: str, default: Decimal) -> Decimal:
        """Finds multiplier by charge code."""
        for item in self.items:
            if item.charge_code == charge_code:
                return item.rate
        return default

    def get_flat_rate(self, charge_code: str, size_ft: Optional[int] = None) -> Decimal:
        """Gets flat fee or rate by charge code, optionally matching size_ft."""
        for item in self.items:
            if item.charge_code == charge_code:
                if size_ft is not None:
                    if item.size_ft == size_ft:
                        return item.rate
                else:
                    return item.rate
        return Decimal("0.00")
