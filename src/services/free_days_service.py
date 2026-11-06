"""
Service: Free Days Service.
Implements BR-03: Free Days Calculation and Sunday/Holiday Extensions.
"""
from datetime import date, datetime, timedelta
from typing import Dict, Optional, Set, Tuple
from src.models.container import Container
from src.models.vessel import Vessel
from src.utils.constants import ContainerType, Direction
from src.utils.date_utils import calculate_last_free_day, is_non_working_day


class FreeDaysService:
    def __init__(self, holidays: Set[date], free_days_rules: Dict[Tuple[str, str], int]):
        self.holidays = holidays
        self.free_days_rules = free_days_rules

    def get_import_free_days_count(self, container_type: ContainerType) -> int:
        """Looks up import free days count by container type."""
        t_str = container_type.value
        if ("IMPORT", t_str) in self.free_days_rules:
            return self.free_days_rules[("IMPORT", t_str)]
        return 3

    def calculate_import_last_free_day(self, discharge_ts: datetime, container_type: ContainerType) -> date:
        """
        Calculates last free day for import container.
        Counted from discharge completion date.
        If last free day falls on Sunday or terminal holiday, extends to next working day.
        """
        start_date = discharge_ts.date()
        count = self.get_import_free_days_count(container_type)
        return calculate_last_free_day(start_date, count, self.holidays)

    def calculate_export_free_window(self, vessel_eta: datetime) -> Tuple[date, date]:
        """
        Export containers: 5 free days before vessel ETA.
        Returns (free_window_start_date, free_window_end_date).
        Any storage prior to free_window_start_date is chargeable.
        """
        eta_date = vessel_eta.date()
        # 5 free days ending on eta_date
        start_date = eta_date - timedelta(days=5)
        return (start_date, eta_date)

    def calculate_empty_last_free_day(self, empty_gate_in_ts: datetime) -> date:
        """EMPTY containers have 1 free day from empty gate-in."""
        start_date = empty_gate_in_ts.date()
        return calculate_last_free_day(start_date, 1, self.holidays)

    def calculate_shutout_restart_last_free_day(self, shut_out_ts: datetime) -> date:
        """SHUT_OUT restart gives 2 free days."""
        start_date = shut_out_ts.date()
        return calculate_last_free_day(start_date, 2, self.holidays)

