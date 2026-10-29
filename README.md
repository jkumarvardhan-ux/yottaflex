# YottaFlex.ai – Dock & Yard Appointment Scheduler

**72-Hour Code Challenge – Round 2**

End-to-end synthetic data generation and scheduling workflow for **inbound/outbound appointments** constrained by dock capacity, yard slots, labor shifts, vehicle compatibility and time windows.

## Problem Statement

Schedule inbound/outbound appointments against dock, yard, labor, vehicle and time-window constraints.

The solution exposes key decisions and exceptions, preserves full traceability (event history is never overwritten), and produces measurable outputs (utilization, wait times, exception rates).

## Solution Overview

This repository implements:

1. **Master data generation** – Facility → Dock → YardSlot → Carrier → Vehicle
2. **Transactional data** – Appointment, Shipment, LaborShift, HandlingRequirement
3. **Event simulation** – Check-in, unloading/loading, departure, no-shows, early arrivals, congestion
4. **Business rules engine** – Capacity calendars, compatibility checks, service durations
5. **Edge-case injection** with labelled ground truth
6. **Deterministic generation** (fixed seed `20261022`) + reproducibility verification
7. **Full validation suite** (PK uniqueness, FK integrity, lifecycle, capacity, derived metrics)
8. **Clean exports** – CSV + JSON + SQL schema + data dictionary + ground_truth

### Suggested Volume (configurable)

| Entity            | Count      |
|-------------------|------------|
| Facilities        | 10         |
| Docks             | 100        |
| Appointments      | 20 000     |
| Events            | ~100 000   |
| Time horizon      | 60 days    |

A smaller “starter” mode is available for quick local runs.

## Quick Start

```bash
# 1. Clone / enter repo
cd yottaflex-dock-scheduler

# 2. Create virtualenv (recommended)
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Generate full dataset (takes ~1–3 min depending on machine)
python -m src.generate --mode full --seed 20261022

# 5. Or generate starter dataset (fast)
python -m src.generate --mode starter --seed 20261022

# 6. Validate
python -m src.validate

# 7. Reproducibility check (regenerate twice & compare)
python -m src.reproducibility_check

# 8. Launch interactive dashboard
streamlit run src/dashboard.py
```

### Interactive Dashboard

After generating data, open a live browser dashboard:

```bash
streamlit run src/dashboard.py
```

Pages included:
- **Overview** – KPIs, status mix, daily volume, exception severity
- **Appointments** – filters, service duration distribution
- **Dock Utilization** – per-dock and per-type utilization
- **Events Timeline** – event type mix + per-appointment timeline
- **Exceptions & Ground Truth** – labelled edge cases
- **Shipments & Handling** – commodities, weight, special handling
- **Master Data** – facilities, docks, carriers, vehicles
- **Raw Tables** – browse & download any CSV

Generated artefacts land in `data/`:

```
data/
├── csv/
│   ├── facilities.csv
│   ├── docks.csv
│   ├── yard_slots.csv
│   ├── carriers.csv
│   ├── vehicles.csv
│   ├── appointments.csv
│   ├── shipments.csv
│   ├── labor_shifts.csv
│   ├── handling_requirements.csv
│   ├── check_in_events.csv
│   ├── exceptions.csv
│   └── ground_truth.csv
├── json/               # same entities as JSON
├── schema.sql
├── data_dictionary.md
├── generation_manifest.json
└── validation_report.json
```

## Project Layout

```
yottaflex-dock-scheduler/
├── README.md
├── requirements.txt
├── LICENSE
├── src/
│   ├── __init__.py
│   ├── config.py              # volumes, seed, constants
│   ├── models.py              # dataclasses / entity definitions
│   ├── data_dictionary.py     # field-level dictionary
│   ├── generators/
│   │   ├── master.py          # Facility, Dock, YardSlot, Carrier, Vehicle
│   │   ├── transactional.py   # Appointment, Shipment, LaborShift, HandlingReq
│   │   ├── events.py          # CheckInEvent + state machine
│   │   └── exceptions.py      # labelled edge cases
│   ├── business_rules.py      # capacity calendars, compatibility, durations
│   ├── generate.py            # main CLI entry point
│   ├── validate.py            # acceptance criteria checks
│   └── reproducibility_check.py
├── docs/
│   ├── data_dictionary.md
│   ├── schema.md
│   └── architecture.md
├── data/                      # generated artefacts (gitignored by default)
├── tests/
│   └── test_basic.py
└── scripts/
    └── export_sql.py
```

## ID / Nomenclature Conventions

| Entity            | Pattern                              | Example              |
|-------------------|--------------------------------------|----------------------|
| Facility          | `FAC-XXX`                            | `FAC-001`            |
| Dock              | `DOCK-<facility>-XXX`                | `DOCK-FAC-001-001`   |
| YardSlot          | `YS-<dock>-XXX`                      | `YS-DOCK-FAC-001-001-01` |
| Carrier           | `CAR-XXXX`                           | `CAR-0001`           |
| Vehicle           | `VEH-<carrier>-XXX`                  | `VEH-CAR-0001-001`   |
| Appointment       | `APPT-YYYY-NNNNNN`                   | `APPT-2026-000001`   |
| Shipment          | `SHP-YYYY-NNNNNN`                    | `SHP-2026-000001`    |
| Check-in Event    | `CHECK-<appointment>-NN`             | `CHECK-APPT-2026-000001-01` |
| Exception         | `EXC-NNNNNN`                         | `EXC-000001`         |

All IDs are deterministic given the seed. Counters are zero-padded and immutable.

## Core Business Rules Implemented

1. **Capacity calendars** – each dock has a daily slot capacity (configurable by type).
2. **Compatibility** – vehicle type ↔ dock equipment ↔ handling requirements (refrigerated / hazardous / standard).
3. **Service durations** – derived from shipment weight, handling type and dock equipment.
4. **Labor shifts** – appointments can only be scheduled when a matching LaborShift is available.
5. **Lifecycle** – Appointment states: `REQUESTED → CONFIRMED → CHECKED_IN → LOADING → DEPARTED | NO_SHOW | CANCELLED`.
6. **Event history** – every state transition is an immutable `CheckInEvent` (or Exception) record. History is never overwritten.
7. **Exception injection** (labelled):
   - Overlapping appointments exceed dock capacity
   - Incompatible load assigned to dock
   - Check-in before appointment window
   - Labor shift not available
   - No-show not recorded (missing event)

## Ground Truth

`data/csv/ground_truth.csv` contains one row per injected anomaly with:

- `entity_id`
- `issue_type`
- `expected_decision` / `expected_label`
- `rule_reference`
- `severity`

Ground truth is **never** mixed into the feature tables.

## Validation & Acceptance Criteria

The validator enforces:

- Primary-key uniqueness
- Foreign-key integrity (all joins valid)
- Allowed enums & date ordering
- Capacity & compatibility rules
- Lifecycle transition legality
- Derived metrics (utilization, average wait time) are reproducible from source events
- Exception records have cause codes
- Row-count / checksum reproducibility under fixed seed

## Reproducibility

```bash
python -m src.reproducibility_check
```

Regenerates the dataset twice with the same seed and asserts identical row counts + SHA-256 checksums of every CSV.

## License & Provenance

All data is **synthetic**. No external personal or confidential data is used.  
Fixed seed, generator command and source manifest are recorded in `data/generation_manifest.json` for auditability.

## Contact / Challenge

This submission is for the YottaFlex.ai 72-Hour Code Challenge.  
Questions: contactus@yottaflex.ai

---

**Author**: Challenge participant  
**Seed**: `20261022`  
**Generated**: see `data/generation_manifest.json`
