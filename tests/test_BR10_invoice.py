"""
Tests for BR-10: Invoicing, GST, Manager Approval, and Late Payment Interest.
"""
from datetime import date, datetime
from decimal import Decimal
import pytest
from src.models.container import Container
from src.models.tariff import TariffItem, TariffTable
from src.services.billing_service import BillingService
from src.services.demurrage_service import DemurrageService
from src.services.detention_service import DetentionService
from src.services.free_days_service import FreeDaysService
from src.services.operations_service import OperationsService
from src.services.reefer_service import ReeferService
from src.utils.constants import ChargeCode, ContainerType, Direction


@pytest.fixture
def sample_tariff():
    items = [
        TariffItem(ChargeCode.DEMURRAGE_DRY.value, Decimal("1200.00"), "per day", 20, 1, 5),
        TariffItem(ChargeCode.DEMURRAGE_DRY.value, Decimal("2000.00"), "per day", 20, 6, 10),
        TariffItem(ChargeCode.DEMURRAGE_DRY.value, Decimal("3500.00"), "per day", 20, 11, None),
        TariffItem(ChargeCode.SIZE_MULT_40.value, Decimal("1.60"), "multiplier", 40),
        TariffItem(ChargeCode.TYPE_MULT_REEFER.value, Decimal("2.00"), "multiplier"),
        TariffItem(ChargeCode.REEFER_PLUG.value, Decimal("2500.00"), "per day"),
        TariffItem(ChargeCode.LIFT.value, Decimal("3000.00"), "per lift", 20),
        TariffItem(ChargeCode.LIFT.value, Decimal("4500.00"), "per lift", 40),
        TariffItem(ChargeCode.GST_PCT.value, Decimal("18.00"), "pct"),
        TariffItem(ChargeCode.INTEREST_PCT_PER_MONTH.value, Decimal("1.50"), "pct"),
        TariffItem(ChargeCode.MANAGER_APPROVE_ABOVE.value, Decimal("200000.00"), "per container"),
    ]
    return TariffTable(items)


def test_BR10_invoice_gst_and_subtotal(sample_tariff):
    holidays = set()
    free_days = FreeDaysService(holidays, {("IMPORT", "DRY"): 3})
    dem_service = DemurrageService(sample_tariff, free_days)
    det_service = DetentionService(sample_tariff)
    reefer_service = ReeferService(sample_tariff)
    ops_service = OperationsService(sample_tariff)
    billing = BillingService(sample_tariff, dem_service, det_service, reefer_service, ops_service)

    c = Container("C01", 20, ContainerType.DRY, Decimal("10.00"), Direction.IMPORT, "VSL-01", "KVL", "ICD", "PTY-01")
    c.discharge_ts = datetime(2026, 8, 1, 10, 0, 0)

    # Issue invoice on Aug 5: Lift = 3000, Demurrage = 1200. Subtotal = 4200. GST (18%) = 756.00
    inv, err = billing.issue_invoice("PTY-01", "VSL-01", date(2026, 8, 5), [c])
    assert err is None
    assert inv.subtotal == Decimal("4200.00")
    assert inv.gst_amount == Decimal("756.00")
    assert inv.total_with_gst == Decimal("4956.00")


def test_BR10_manager_approval_above_2_lakh(sample_tariff):
    holidays = set()
    free_days = FreeDaysService(holidays, {("IMPORT", "REEFER"): 5})
    dem_service = DemurrageService(sample_tariff, free_days)
    det_service = DetentionService(sample_tariff)
    reefer_service = ReeferService(sample_tariff)
    ops_service = OperationsService(sample_tariff)
    billing = BillingService(sample_tariff, dem_service, det_service, reefer_service, ops_service)

    # 40-ft Reefer in yard for 7 weeks -> demurrage > 2 lakh
    c = Container("KVLU0898233", 40, ContainerType.REEFER, Decimal("20.00"), Direction.IMPORT, "VSL-01", "KVL", "ICD", "PTY-01")
    c.discharge_ts = datetime(2026, 8, 3, 18, 0, 0)

    # Without approval -> issue invoice fails
    c.manager_approved = False
    inv, err = billing.issue_invoice("PTY-01", "VSL-01", date(2026, 9, 24), [c])
    assert inv is None
    assert "MANAGER_APPROVE" in err

    # With approval -> succeeds
    c.manager_approved = True
    inv, err = billing.issue_invoice("PTY-01", "VSL-01", date(2026, 9, 24), [c])
    assert inv is not None
    assert err is None


def test_BR10_late_payment_interest(sample_tariff):
    holidays = set()
    free_days = FreeDaysService(holidays, {("IMPORT", "DRY"): 3})
    dem_service = DemurrageService(sample_tariff, free_days)
    det_service = DetentionService(sample_tariff)
    reefer_service = ReeferService(sample_tariff)
    ops_service = OperationsService(sample_tariff)
    billing = BillingService(sample_tariff, dem_service, det_service, reefer_service, ops_service)

    c = Container("C01", 20, ContainerType.DRY, Decimal("10.00"), Direction.IMPORT, "VSL-01", "KVL", "ICD", "PTY-01")
    c.discharge_ts = datetime(2026, 8, 1, 10, 0, 0)
    inv, _ = billing.issue_invoice("PTY-01", "VSL-01", date(2026, 8, 5), [c])

    # Paid on day 10 (Aug 15) -> within 15 days -> 0 interest
    billing.record_payment("PTY-01", "VSL-01", date(2026, 8, 15))
    assert inv.calculate_interest() == Decimal("0.00")

    # Paid on day 20 (Aug 25) -> exceeds 15 days -> 1.5% interest
    inv.paid_date = date(2026, 8, 25)
    expected_interest = (inv.total_with_gst * Decimal("0.015")).quantize(Decimal("0.01"))
    assert inv.calculate_interest() == expected_interest

