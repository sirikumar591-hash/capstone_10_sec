# Shipping Container Yard Allocation and Demurrage/Detention Billing Engine

**Project ID:** T090-PS-122  
**Domain:** Port Logistics & Terminal Operations  
**Team Members:**  
1. Sirivalli A R – 1AT24CG081  
2. Spoorthi C V – 1AT24CG082  

---

## 📌 Project Overview
A high-performance, command-file-driven business rules engine that simulates the operations of a container terminal and shipping line. The engine enforces spatial, physical, safety, and financial rules to allocate containers to yard blocks, track lifecycle events, calculate storage, demurrage, reefer plug-in fees, and detention charges, and generate invoices with GST and late payment interest.

---

## ⚙️ Features & Implemented Business Rules (BR-01 to BR-12)

- **BR-01 (Container Stacking):** 20-ft = 1 TEU, 40-ft = 2 TEU (occupies two adjacent bays in the same row and tier). Enforces physical limits (DRY $\le 5$, REEFER $\le 3$, HAZ $\le 2$), slot support from below, heavy containers ($> 28\text{ t}$) on Tier 1 only, and IMO hazard segregation (Classes 1 & 5.1 cannot share with Class 3).
- **BR-02 (Allocation Priority):** Precedence-based slot allocation: Type & Segregation $\rightarrow$ Weight & Tier $\rightarrow$ Same-vessel & destination grouping $\rightarrow$ Lowest occupancy $\rightarrow$ Lowest block ID $\rightarrow$ `OVERFLOW` fallback (1.5x storage multiplier).
- **BR-03 (Free Days):** 3 free calendar days for import DRY/HAZ, 5 free days for REEFER, 5 days prior to ETA for export, 1 day for empty returns. Automatically extends last free day past Sundays and terminal holidays to the next working day.
- **BR-04 (Demurrage Slabs):** 20-ft DRY base rates: Days 1–5 (₹1,200), Days 6–10 (₹2,000), Day 11+ (₹3,500). Multipliers: 40-ft (1.6x), REEFER (2.0x), HAZ (1.5x), OVERFLOW (1.5x). Partial days count as full days.
- **BR-05 (Detention Charges):** Equipment retention fees post-`GATE_OUT`: 7 free days; Days 8–14: ₹1,500/day (20-ft) or ₹2,800/day (40-ft); Day 15+: doubled rates. Stops at `EMPTY_RETURN`.
- **BR-06 (Gate-Out Hold Checks):** Mandatory verification of Customs OOC, Delivery Order, and Terminal Payment. Customs examination locks gate-out and waives demurrage only when exam duration exceeds 2 days (48 hours).
- **BR-07 (Lifts & Restow):** Standard lift charges (₹3,000 for 20-ft, ₹4,500 for 40-ft). Restows for `TERMINAL_ACCESS` billed to `TERMINAL`; restows for `CONSIGNEE_REQUEST` billed to consignee party.
- **BR-08 (Shut-Out):** Line cut-off miss incurs ₹5,000 fee with 2 free days storage restart. Terminal yard congestion incurs ₹0 fee with 2 free days restart.
- **BR-09 (Long-Stay & Auction):** Containers staying $> 30$ days in yard marked `AUCTION_LISTED`. Demurrage capped at $\text{Slab-3 rate} \times 45\text{ days}$ from Day 45 with ₹10,000 auction processing fee. ₹2,000 delisting fee upon gate-out.
- **BR-10 (Invoices & Taxes):** Generated per party and vessel (`INV-<party_id>-<vessel_id>`). Applies 18% GST. Demurrage $> \text{₹}2,00,000$ requires `MANAGER_APPROVE`. 1.5% monthly interest on unpaid invoices after 15 days.
- **BR-11 (Reefer Specifics):** ₹2,500/day plug-in fee from day 1 (no free days). Temperature deviations $> 4$ hours trigger `CLAIM_RISK` and pause plug-in billing.
- **BR-12 (Precedence):** Strict execution order for slot placement and financial calculations.

---

## 📁 Project Structure

```
CAPSTONE_10 SEC/
│
├── data/                           # Master datasets and command script
│   ├── commands.txt
│   ├── consignees.csv
│   ├── containers.csv
│   ├── free_days.csv
│   ├── holidays.csv
│   ├── shipping_lines.csv
│   ├── tariff.csv
│   ├── vessels.csv
│   └── yard_blocks.csv
│
├── outputs/                        # Output evaluation reports
│   ├── allocations.csv
│   ├── container_ledger.csv
│   ├── yard_occupancy.csv
│   └── invoices.csv
│
├── src/                            # Source code
│   ├── main.py                     # Entry point
│   ├── config.py                   # Paths and configuration
│   ├── models/                     # Domain entities (Container, YardBlock, Tariff, etc.)
│   ├── services/                   # Business rule services and command orchestrator
│   ├── validators/                 # Input and state integrity validation
│   └── utils/                      # Date, currency Decimal, and constant helpers
│
├── tests/                          # Pytest automated test suite (42 tests)
│   ├── test_BR01_stacking.py
│   ├── test_BR02_allocation.py
│   ├── test_BR03_free_days.py
│   ├── test_BR04_demurrage.py
│   ├── test_BR05_detention.py
│   ├── test_BR06_gate_out.py
│   ├── test_BR07_restow.py
│   ├── test_BR08_shutout.py
│   ├── test_BR09_long_stay.py
│   ├── test_BR10_invoice.py
│   ├── test_BR11_reefer.py
│   ├── test_BR12_precedence.py
│   ├── test_edge_cases.py          # Planted README edge cases (EC-01 to EC-08)
│   └── test_validation.py          # Input integrity validation tests
│
├── requirements.txt
├── .gitignore
└── README.md
```

---

## 🚀 Execution Instructions

### 1. Run the Main Application
Processes all 831 commands from `data/commands.txt` and populates the `outputs/` directory:
```bash
python src/main.py
```

### 2. Run the Automated Test Suite
Executes all 42 automated unit, rule, edge-case, and validation tests:
```bash
python -m pytest tests/ -v
```

