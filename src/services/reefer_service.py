"""
Service: Reefer Management and Temperature Monitoring.
Implements BR-11: Reefer Plug-in Billing and Temperature Deviation Handling.
"""
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Tuple
from src.models.container import Container
from src.models.tariff import TariffTable
from src.utils.constants import ChargeCode, ContainerType, Flag
from src.utils.money_utils import round_money, to_decimal


class ReeferService:
    def __init__(self, tariff: TariffTable):
        self.tariff = tariff

    def process_temperature_deviation(
        self,
        container: Container,
        start_ts: datetime,
        end_ts: datetime,
        recorded_temp_c: Decimal,
    ) -> bool:
        """
        BR-11: Processes temperature deviation.
        - Duration strictly > 4 hours:
          - Flag CLAIM_RISK
          - Pause plug-in billing for the deviation duration
        - Duration <= 4 hours:
          - No CLAIM_RISK
          - No billing pause
        Returns True if CLAIM_RISK was flagged, False otherwise.
        """
        duration_seconds = (end_ts - start_ts).total_seconds()
        four_hours_seconds = 4 * 3600

        if duration_seconds > four_hours_seconds:
            container.flags.add(Flag.CLAIM_RISK.value)
            container.temperature_deviations.append((start_ts, end_ts, recorded_temp_c))
            return True
        return False

    def calculate_plugin_charge(
        self,
        container: Container,
        as_of_dt: datetime,
    ) -> Decimal:
        """
        Calculates reefer plug-in charges.
        - ₹2,500 per day from Day 1 in yard.
        - No free days for plug-in charges.
        - Subtracts paused duration from qualifying temperature deviations (> 4h).
        """
        if container.container_type != ContainerType.REEFER or not container.discharge_ts:
            return Decimal("0.00")

        end_dt = container.gate_out_ts if container.gate_out_ts else as_of_dt
        if end_dt < container.discharge_ts:
            return Decimal("0.00")

        daily_rate = self.tariff.get_flat_rate(ChargeCode.REEFER_PLUG.value)
        
        # Calendar days in yard
        start_d = container.discharge_ts.date()
        end_d = end_dt.date()
        total_days = (end_d - start_d).days
        if end_dt.time() > datetime.min.time():
            total_days += 1

        total_charge = daily_rate * Decimal(total_days)

        # Deduct paused hours for deviations > 4 hours
        total_paused_seconds = 0.0
        for dev_start, dev_end, _ in container.temperature_deviations:
            # Overlap between [discharge_ts, end_dt] and [dev_start, dev_end]
            actual_start = max(container.discharge_ts, dev_start)
            actual_end = min(end_dt, dev_end)
            if actual_start < actual_end:
                total_paused_seconds += (actual_end - actual_start).total_seconds()

        if total_paused_seconds > 0:
            hourly_rate = daily_rate / Decimal("24.00")
            paused_hours = Decimal(str(total_paused_seconds / 3600.0))
            deduction = hourly_rate * paused_hours
            total_charge = max(Decimal("0.00"), total_charge - deduction)

        return round_money(total_charge)

