"""
Main entry point for synthetic data generation.
Usage:
    python -m src.generate --mode starter|full --seed 20261022
"""

from __future__ import annotations
import argparse
import json
import hashlib
import random
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from tqdm import tqdm

from .config import (
    DEFAULT_SEED,
    VOLUMES,
    DATA_DIR,
    CSV_DIR,
    JSON_DIR,
    START_DATE,
    HORIZON_DAYS,
)
from .generators.master import (
    generate_facilities,
    generate_docks,
    generate_yard_slots,
    generate_carriers,
    generate_vehicles,
)
from .generators.transactional import (
    generate_labor_shifts,
    generate_appointments_and_shipments,
)
from .generators.events import generate_all_events
from .generators.exceptions import inject_edge_cases


def _ensure_dirs():
    CSV_DIR.mkdir(parents=True, exist_ok=True)
    JSON_DIR.mkdir(parents=True, exist_ok=True)


def _write_df(df: pd.DataFrame, name: str):
    csv_path = CSV_DIR / f"{name}.csv"
    json_path = JSON_DIR / f"{name}.json"
    df.to_csv(csv_path, index=False)
    df.to_json(json_path, orient="records", indent=2, date_format="iso")
    return csv_path


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def run(mode: str = "starter", seed: int = DEFAULT_SEED) -> dict:
    _ensure_dirs()
    rng = random.Random(seed)
    vol = VOLUMES[mode]

    print(f"=== YottaFlex Synthetic Data Generator ===")
    print(f"Mode : {mode}")
    print(f"Seed : {seed}")
    print(f"Volume: {vol}")
    print()

    # 1. Master data
    print("→ Generating master data …")
    facilities = generate_facilities(vol["n_facilities"], rng)
    docks = generate_docks(facilities, vol["n_docks_per_facility"], rng)
    yard_slots = generate_yard_slots(docks, slots_per_dock=2)
    carriers = generate_carriers(vol["n_carriers"], rng)
    vehicles = generate_vehicles(carriers, vol["n_vehicles_per_carrier"], rng)

    # 2. Labor
    print("→ Generating labor shifts …")
    labor_shifts = generate_labor_shifts(
        facilities, vol["n_labor_shifts_per_facility_day"], rng
    )

    # 3. Appointments + Shipments + Handling
    print("→ Generating appointments, shipments & handling requirements …")
    appointments, shipments, handling_reqs = generate_appointments_and_shipments(
        facilities, docks, yard_slots, carriers, vehicles, labor_shifts,
        vol["n_appointments"], rng,
    )

    # 4. Events (baseline)
    print("→ Simulating check-in / loading / departure events …")
    events, appointments = generate_all_events(appointments, rng)

    # 5. Edge-case injection
    print("→ Injecting labelled edge cases …")
    appointments, extra_events, exceptions, ground_truth = inject_edge_cases(
        appointments, docks, vehicles, labor_shifts, events,
        vol["edge_case_fraction"], rng,
    )
    events = events + extra_events

    # 6. Persist
    print("→ Writing CSV / JSON …")
    tables = {
        "facilities": facilities,
        "docks": docks,
        "yard_slots": yard_slots,
        "carriers": carriers,
        "vehicles": vehicles,
        "labor_shifts": labor_shifts,
        "appointments": appointments,
        "shipments": shipments,
        "handling_requirements": handling_reqs,
        "check_in_events": events,
        "exceptions": exceptions,
        "ground_truth": ground_truth,
    }

    checksums = {}
    row_counts = {}
    for name, rows in tables.items():
        df = pd.DataFrame(rows)
        path = _write_df(df, name)
        checksums[name] = _sha256_file(path)
        row_counts[name] = len(df)
        print(f"   {name:25s} {len(df):7d} rows")

    # 7. Manifest
    manifest = {
        "generator": "yottaflex-dock-scheduler",
        "version": "1.0.0",
        "mode": mode,
        "seed": seed,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "horizon": {
            "start": START_DATE.isoformat(),
            "days": HORIZON_DAYS,
        },
        "volumes_requested": vol,
        "row_counts": row_counts,
        "checksums_sha256": checksums,
        "command": f"python -m src.generate --mode {mode} --seed {seed}",
        "notes": "All data is synthetic. No external PII used.",
    }
    manifest_path = DATA_DIR / "generation_manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"\nManifest written → {manifest_path}")

    # 8. Schema SQL (simple)
    _write_schema_sql()

    print("\n✅ Generation complete.")
    return manifest


def _write_schema_sql():
    sql = """
-- YottaFlex Dock & Yard Appointment Scheduler – schema
-- Deterministic synthetic data; seed recorded in generation_manifest.json

CREATE TABLE IF NOT EXISTS facilities (
    facility_id     VARCHAR(16) PRIMARY KEY,
    name            VARCHAR(128) NOT NULL,
    facility_type   VARCHAR(32)  NOT NULL,
    city            VARCHAR(64),
    state           VARCHAR(8),
    country         VARCHAR(32),
    timezone        VARCHAR(64),
    open_time       VARCHAR(8),
    close_time      VARCHAR(8),
    is_active       BOOLEAN DEFAULT TRUE,
    effective_from  DATE,
    effective_to    DATE
);

CREATE TABLE IF NOT EXISTS docks (
    dock_id             VARCHAR(32) PRIMARY KEY,
    facility_id         VARCHAR(16) REFERENCES facilities(facility_id),
    dock_number         INTEGER,
    dock_type           VARCHAR(32),
    max_vehicle_length_m NUMERIC(6,1),
    has_leveler         BOOLEAN,
    has_reefer_hookup   BOOLEAN,
    has_hazmat_cert     BOOLEAN,
    daily_capacity      INTEGER,
    is_active           BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS yard_slots (
    yard_slot_id    VARCHAR(48) PRIMARY KEY,
    dock_id         VARCHAR(32) REFERENCES docks(dock_id),
    facility_id     VARCHAR(16) REFERENCES facilities(facility_id),
    slot_number     INTEGER,
    max_dwell_hours NUMERIC(4,1),
    is_covered      BOOLEAN,
    is_active       BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS carriers (
    carrier_id      VARCHAR(16) PRIMARY KEY,
    name            VARCHAR(128),
    scac            VARCHAR(8),
    contact_email   VARCHAR(128),
    is_preferred    BOOLEAN,
    is_active       BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS vehicles (
    vehicle_id      VARCHAR(32) PRIMARY KEY,
    carrier_id      VARCHAR(16) REFERENCES carriers(carrier_id),
    vehicle_type    VARCHAR(32),
    license_plate   VARCHAR(16),
    max_weight_kg   NUMERIC(10,1),
    length_m        NUMERIC(5,1),
    has_reefer      BOOLEAN,
    has_hazmat_cert BOOLEAN,
    is_active       BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS labor_shifts (
    labor_shift_id  VARCHAR(48) PRIMARY KEY,
    facility_id     VARCHAR(16) REFERENCES facilities(facility_id),
    shift_date      DATE,
    start_time      VARCHAR(8),
    end_time        VARCHAR(8),
    role            VARCHAR(32),
    headcount       INTEGER,
    is_available    BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS appointments (
    appointment_id          VARCHAR(24) PRIMARY KEY,
    facility_id             VARCHAR(16) REFERENCES facilities(facility_id),
    dock_id                 VARCHAR(32) REFERENCES docks(dock_id),
    yard_slot_id            VARCHAR(48),
    carrier_id              VARCHAR(16) REFERENCES carriers(carrier_id),
    vehicle_id              VARCHAR(32) REFERENCES vehicles(vehicle_id),
    shipment_id             VARCHAR(24),
    appointment_type        VARCHAR(16),
    requested_date          DATE,
    requested_window_start  VARCHAR(8),
    requested_window_end    VARCHAR(8),
    confirmed_date          DATE,
    confirmed_window_start  VARCHAR(8),
    confirmed_window_end    VARCHAR(8),
    status                  VARCHAR(16),
    service_duration_min    INTEGER,
    created_at              TIMESTAMP,
    updated_at              TIMESTAMP
);

CREATE TABLE IF NOT EXISTS shipments (
    shipment_id     VARCHAR(24) PRIMARY KEY,
    appointment_id  VARCHAR(24) REFERENCES appointments(appointment_id),
    carrier_id      VARCHAR(16),
    vehicle_id      VARCHAR(32),
    direction       VARCHAR(16),
    weight_kg       NUMERIC(10,1),
    volume_cbm      NUMERIC(8,1),
    commodity       VARCHAR(64),
    is_refrigerated BOOLEAN,
    is_hazardous    BOOLEAN,
    is_oversize     BOOLEAN,
    origin          VARCHAR(128),
    destination     VARCHAR(128)
);

CREATE TABLE IF NOT EXISTS handling_requirements (
    handling_req_id     VARCHAR(16) PRIMARY KEY,
    shipment_id         VARCHAR(24) REFERENCES shipments(shipment_id),
    handling_type       VARCHAR(32),
    temperature_min_c   NUMERIC(5,1),
    temperature_max_c   NUMERIC(5,1),
    hazmat_class        VARCHAR(8),
    special_equipment   VARCHAR(64),
    service_duration_min INTEGER
);

CREATE TABLE IF NOT EXISTS check_in_events (
    event_id        VARCHAR(48) PRIMARY KEY,
    appointment_id  VARCHAR(24) REFERENCES appointments(appointment_id),
    facility_id     VARCHAR(16),
    dock_id         VARCHAR(32),
    event_type      VARCHAR(32),
    event_ts        TIMESTAMP,
    sequence        INTEGER,
    actor_role      VARCHAR(32),
    notes           TEXT,
    wait_time_min   INTEGER,
    dwell_time_min  INTEGER
);

CREATE TABLE IF NOT EXISTS exceptions (
    exception_id    VARCHAR(16) PRIMARY KEY,
    entity_type     VARCHAR(32),
    entity_id       VARCHAR(48),
    issue_type      VARCHAR(32),
    severity        VARCHAR(16),
    detected_at     TIMESTAMP,
    description     TEXT,
    cause_code      VARCHAR(32),
    resolved        BOOLEAN DEFAULT FALSE,
    resolution_notes TEXT
);

CREATE TABLE IF NOT EXISTS ground_truth (
    gt_id               VARCHAR(16) PRIMARY KEY,
    entity_type         VARCHAR(32),
    entity_id           VARCHAR(48),
    issue_type          VARCHAR(32),
    expected_label      VARCHAR(64),
    expected_decision   VARCHAR(64),
    rule_reference      VARCHAR(32),
    severity            VARCHAR(16),
    injected            BOOLEAN DEFAULT TRUE
);
"""
    path = DATA_DIR / "schema.sql"
    path.write_text(sql.strip() + "\n")
    print(f"Schema written → {path}")


def main():
    parser = argparse.ArgumentParser(description="YottaFlex synthetic data generator")
    parser.add_argument("--mode", choices=["starter", "full"], default="starter")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args()
    run(mode=args.mode, seed=args.seed)


if __name__ == "__main__":
    main()
