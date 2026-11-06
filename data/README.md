# PS-122 – Shipping Container Yard Allocation and Demurrage/Detention Billing Engine — Sample Data Pack

Prepared by 10 SECONDS for Team T090.

## Files

| File | What it holds | Row count |
|---|---|---|
| `yard_blocks.csv` | 12 yard blocks (6 DRY, 2 REEFER, 2 HAZ, 2 EMPTY) with geometry and tier limits | 12 data rows |
| `tariff.csv` | Demurrage slabs, multipliers, detention, lift, fees, GST and interest | 18 data rows |
| `free_days.csv` | Free-day rules by movement and type | 6 data rows |
| `holidays.csv` | Terminal holidays (Sundays are also non-working for free-day extension) | 3 data rows |
| `shipping_lines.csv` | 3 shipping lines | 3 data rows |
| `vessels.csv` | 4 vessel calls with ETA, ETD and export cut-off | 4 data rows |
| `consignees.csv` | 8 consignees / shippers | 8 data rows |
| `containers.csv` | 300 containers: discharge lists (imports, in discharge order) and export load lists | 300 data rows |
| `commands.txt` | ~400 gate/exam/restow/shut-out/return/temperature/payment events over 60 days, plus vessel discharge/load operations, invoices and prints | 831 command lines (excluding comments) |

Row numbers quoted below are 1-based data-row numbers (the header is row 0). Line numbers for `commands.txt` are physical line numbers including comment lines.

## Column reference

Conventions: dates `YYYY-MM-DD`; timestamps `YYYY-MM-DD HH:MM:SS` (24h, IST, no timezone suffix); money in Rs as plain decimals with 2 places (no commas, no symbol); percentages as plain numbers (12.5 means 12.5%); booleans `true`/`false`; IDs uppercase with a fixed prefix. An empty cell means "not applicable" and is only allowed where the notes say so.

### `yard_blocks.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| block_id | string | XX-nn | — | tie-break: lowest id |
| block_type | enum | — | DRY, REEFER, HAZ, EMPTY | — |
| rows | int | — | — | — |
| bays_per_row | int | — | — | 20-ft ground positions per row |
| max_tiers | int | — | — | physical; rule limits DRY 5, REEFER 3, HAZ 2 |
| capacity_teu | int | TEU | — | — |
| plug_points | int | — | — | REEFER blocks only |

### `tariff.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| charge_code | string | — | — | — |
| size_ft | int | ft | 20, 40 | empty = any |
| slab_from_day | int | — | — | demurrage/detention day, empty = n/a |
| slab_to_day | int | — | — | empty = open-ended |
| rate | decimal | Rs or multiplier | — | see unit |
| unit | string | — | — | — |
| notes | string | — | — | may be empty |

### `free_days.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| movement | enum | — | IMPORT, EXPORT, EMPTY, SHUT_OUT_RESTART | — |
| container_type | string | — | — | — |
| free_days | int | days | — | calendar days |
| counted_from | string | — | — | — |

### `holidays.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| holiday_date | date | — | — | — |
| holiday_name | string | — | — | — |

### `shipping_lines.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| line_code | string | — | — | — |
| line_name | string | — | — | — |
| owner_prefix | string | 4 letters | — | container number prefix |

### `vessels.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| vessel_id | string | VSL-nn | — | — |
| vessel_name | string | — | — | — |
| voyage_no | string | — | — | — |
| line_code | string | — | shipping_lines.csv | — |
| eta | timestamp | — | — | export free days count back from here |
| etd | timestamp | — | — | — |
| export_cutoff | timestamp | — | — | gate-in after this = line cut-off miss |

### `consignees.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| party_id | string | PTY-nn | — | — |
| party_name | string | — | — | — |
| gstin | string | 15 chars | — | — |
| city | string | — | — | — |

### `containers.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| container_no | string | AAAU9999999 | — | — |
| size_ft | int | ft | 20, 40 | 20 = 1 TEU, 40 = 2 TEU |
| container_type | enum | — | DRY, REEFER, HAZ | — |
| gross_weight_t | decimal | t | — | > 28 t = tier 1 only |
| imo_class | string | — | 1, 3, 5.1, 6.1, 8, 9 | HAZ only |
| direction | enum | — | IMPORT, EXPORT | — |
| vessel_id | string | — | vessels.csv | discharging (IMPORT) or loading (EXPORT) vessel |
| line_code | string | — | shipping_lines.csv | detention is billed by this line |
| destination | string | — | — | grouping key with vessel_id |
| party_id | string | — | consignees.csv | consignee (IMPORT) or shipper (EXPORT) |
| set_temp_c | decimal | deg C | — | REEFER only |

## Command file format

`commands.txt` holds one command per line in the form `COMMAND_NAME|arg1|arg2|...`. Commands must be processed strictly in file order. Lines starting with `#` are comments and blank lines are ignored. An argument written as `-` means "not applicable". Every command used in this pack:

| Command | Arguments (in order) | Meaning |
|---|---|---|
| `DISCHARGE_COMPLETE` | `vessel_id|ts` | Allocate the vessel's import list in file order; import free days start |
| `GATE_IN` | `container_no|ts` | Export container arrives by road |
| `GATE_OUT` | `container_no|ts|customs_ooc|delivery_order|payment_receipt` | Hold checks; payment_receipt `-` = not paid |
| `EMPTY_RETURN` | `container_no|ts` | Empty back at the terminal: detention stops, allocate to an EMPTY block |
| `EXAM_START` | `container_no|ts` | Customs examination start |
| `EXAM_END` | `container_no|ts` | — |
| `RESTOW` | `container_no|ts|reason|to_block` | reason CONSIGNEE_REQUEST or TERMINAL_ACCESS; to_block `-` = same block |
| `SHUT_OUT` | `container_no|ts|reason` | reason LINE_CUTOFF or YARD_CONGESTION |
| `LOAD` | `container_no|vessel_id|ts` | Loaded on board |
| `TEMP_DEVIATION` | `container_no|start_ts|end_ts|recorded_temp_c` | Reefer temperature excursion |
| `MANAGER_APPROVE` | `container_no|date` | Approval for demurrage above Rs 2 lakh |
| `ISSUE_INVOICE` | `party_id|vessel_id|date` | Invoice per consignee per vessel |
| `INVOICE_PAYMENT` | `party_id|vessel_id|date|FULL` | — |
| `PRINT_LEDGER` | `container_no|as_of_date` | — |
| `PRINT_YARD_OCCUPANCY` | `date` | — |
| `PRINT_INVOICE` | `party_id|vessel_id` | — |

## Planted scenarios

Every edge case in the brief, mapped to the exact record where it occurs, followed by extra traps.

- **EC-01 Last free day falling on a Sunday followed by a Monday holiday**
  - KVLU5744158 (VSL-04 import, DRY 20): discharge completes 2026-09-10 14:00; 3 free days end Sun 2026-09-13 -> extend past Sunday to Mon 2026-09-14, which is a holiday -> last free day Tue 2026-09-15; demurrage from 2026-09-16, gate-out 2026-09-18 11:30 (3 days) — `containers.csv row 212; commands.txt lines 397, 477`
- **EC-02 Container gate-out at 00:05 on day 6 (partial day)**
  - DCSU7125204 (40-ft DRY, VSL-02): last free day 2026-08-17; GATE_OUT at 2026-08-23 00:05 = 5 minutes into demurrage day 6 — day 6 counts as a full day at the slab-2 rate (x1.6 for 40-ft) — `commands.txt line 214`
- **EC-03 IMO class 3 arriving at a block already holding class 5.1**
  - DCSU3143954 (IMO class 3, VSL-02) arrives while HZ-01 still holds class 5.1 container KVLU6134069 (gates out 2026-08-20) — segregation forbids HZ-01, allocate to HZ-02 — `containers.csv row 187, containers.csv row 186`
- **EC-04 Overweight 40-ft needing tier 1 in a full block**
  - ARLU1838149 (40-ft DRY, 29.40 t > 28 t, VSL-03 -> CFS Mangaluru): its 22 same-group containers fill the ground tier of DR-01 first, so DR-01 has no free tier-1 pair — the overweight box goes to the next block in allocation order (DR-04) — `containers.csv row 211; commands.txt line 224`
- **EC-05 Customs examination of exactly 2 days**
  - DCSU1162695: customs examination 2026-08-14 12:00:00 to 2026-08-16 12:00:00 = exactly 2 days — NOT more than 2, so no demurrage waiver; DCSU9027105 examined for 3 days — waiver for the examination days — `commands.txt lines 110, 111, 152, 158`
- **EC-06 Long-stay cap reached when slab 3 started on day 11**
  - KVLU6594605 (VSL-01, discharged 2026-08-03 18:00) never gates out: demurrage slab 3 starts on demurrage day 11; AUCTION_LISTED after 30 days in yard; from day 45 demurrage is capped at slab-3 rate x 45 days and Rs 10000.00 auction processing fee added (still in yard on 2026-09-29) — `containers.csv row 216`
- **EC-07 Empty return on the 7th day after gate-out**
  - KVLU8300071 (40-ft): GATE_OUT then EMPTY_RETURN on the 7th day after gate-out (within 7 x 24 h) — inside the 7 free detention days, no detention — `commands.txt lines 3, 65`
- **EC-08 Reefer temperature deviation of exactly 4 hours**
  - ARLU5557223 (reefer -18 C): TEMP_DEVIATION lasting exactly 4 h — not longer than 4 h, so no CLAIM_RISK and plug-in billing is NOT paused; ARLU8302265: 5 h deviation — CLAIM_RISK and 5 h plug-in pause — `commands.txt lines 261, 262`
- **Extra traps (not in the brief, but realistic):**
  - ARLU1807567 (IMO class 1, VSL-03): may share with 5.1 but not with class 3 — HZ-02 (holding class 3) is excluded — `containers.csv row 188`
  - DCSU3059061: first GATE_OUT attempt with customs OOC=false and no payment receipt — REFUSED (hold); the later attempt succeeds — `commands.txt lines 145, 154`
  - DCSU7553548: RESTOW at the consignee's request (change of destination block) — lift charged to the consignee; RESTOW events with reason TERMINAL_ACCESS are terminal's cost — `commands.txt lines 68, 125, 285, 330, 341`
  - DCSU2853959: gated in AFTER VSL-02's export cut-off — SHUT_OUT (LINE_CUTOFF): Rs 5000.00 fee, storage restarts with 2 free days, loaded on VSL-03; ARLU3226931: SHUT_OUT for YARD_CONGESTION — free — `commands.txt lines 79, 107, 213, 250, 251, 427`
  - KVLU1179027: export gated in 8 days before VSL-04's ETA — only the last 5 days are free — `commands.txt line 316`
  - KVLU0898233 (40-ft reefer, VSL-01, gate-out 2026-09-24): demurrage x1.6 x2 plus plug-in for ~7 weeks exceeds Rs 2 lakh — needs MANAGER_APPROVE before invoicing (given 2026-08-31, check it is still valid for the final invoice) — `containers.csv row 220`
  - Invoices issued 2026-09-01 for VSL-01/VSL-02: some paid within 15 days, some on day 15 exactly, some later (1.5% per month interest), one in three never paid — `commands.txt lines 321, 322, 323, 324, 325, 326, 327, 328, 329, 501, 502, 503, 504, 505, 506, 507, 508, 509, 510, 511 / payments commands.txt lines 429, 462, 484, 495, 496, 497`

## What is NOT in this pack

Expected outputs are not provided for this set. Validate your engine with your own test suite against the rules in your brief (BR-01 … BR-nn). A separate hidden input set with the same schema will be used at final evaluation; outputs are compared field-for-field, so follow the column formats above exactly in your own output.

## Output format expected at evaluation

Produce these CSV files (header row, same conventions as above, rows sorted as stated). Where the brief is silent on a format detail the choice below is binding for evaluation.

### `allocations.csv`

One row per allocation (discharge, gate-in, empty return, restow), in command order.

Columns, in order: `container_no`, `ts`, `block_id`, `row`, `bay`, `tier`, `reason`

### `container_ledger.csv`

One row per charge line per container, plus a STATE row per state change.

Columns, in order: `container_no`, `line_date`, `state`, `charge_code`, `days`, `rate`, `amount`, `bill_to`, `flags`

### `yard_occupancy.csv`

One row per block.

Columns, in order: `date`, `block_id`, `teu_used`, `capacity_teu`, `occupancy_pct`, `containers`

### `invoices.csv`

One row per invoice line, plus TOTAL, GST and INTEREST rows.

Columns, in order: `invoice_id`, `party_id`, `vessel_id`, `issue_date`, `container_no`, `charge_code`, `amount`

Binding choices: a free period of N days counted from a timestamp ends at 23:59:59 on (that date + N); if that date is a Sunday or holiday it moves to the next working day. Demurrage days are calendar days from 00:00 after the last free day; any part of a day counts as a full day. Within a block, slots are filled lowest tier first, then lowest row, then lowest bay; a 40-ft box needs two adjacent bays of the same row and tier, and any tier above 1 must sit on occupied slots. `state` DISCHARGED, YARD, GATE_OUT, EMPTY_RETURNED, LOADED, RESTOWED, SHUT_OUT, AUCTION_LISTED; invoice_id format INV-<party_id>-<vessel_id>; `flags` CLAIM_RISK, MANAGER_APPROVE_REQUIRED, OVERFLOW.
