"""
Transactional data: LaborShift, Appointment, Shipment, HandlingRequirement.
"""

from __future__ import annotations
import random
from datetime import date, timedelta, datetime, time
from typing import List, Dict, Tuple

from ..config import (
    START_DATE,
    HORIZON_DAYS,
    LABOR_ROLES,
    APPOINTMENT_TYPES,
    HANDLING_TYPES,
    SERVICE_DURATION_BASE_MIN,
)
from ..models import (
    LaborShift, Appointment, Shipment, HandlingRequirement, to_dict,
)
from ..business_rules import (
    is_compatible,
    service_duration_minutes,
    dock_capacity,
)


COMMODITIES = [
    "General Merchandise", "Electronics", "Apparel", "Food (Dry)",
    "Food (Frozen)", "Chemicals", "Automotive Parts", "Building Materials",
    "Pharmaceuticals", "Paper Products", "Furniture", "Beverages",
]


def _date_range(start: date, days: int):
    for i in range(days):
        yield start + timedelta(days=i)


def generate_labor_shifts(
    facilities: List[dict],
    shifts_per_facility_day: int,
    rng: random.Random,
) -> List[dict]:
    shifts = []
    counter = 0
    for fac in facilities:
        for d in _date_range(START_DATE, HORIZON_DAYS):
            for s in range(1, shifts_per_facility_day + 1):
                counter += 1
                role = LABOR_ROLES[(s - 1) % len(LABOR_ROLES)]
                # morning / afternoon / night
                if s == 1:
                    st, et = "06:00", "14:00"
                elif s == 2:
                    st, et = "14:00", "22:00"
                else:
                    st, et = "22:00", "06:00"
                ls_id = f"LS-{fac['facility_id']}-{d.isoformat().replace('-','')}-{s:02d}"
                shift = LaborShift(
                    labor_shift_id=ls_id,
                    facility_id=fac["facility_id"],
                    shift_date=d.isoformat(),
                    start_time=st,
                    end_time=et,
                    role=role,
                    headcount=rng.randint(4, 18),
                    is_available=rng.random() > 0.05,   # 5 % unavailable
                )
                shifts.append(to_dict(shift))
    return shifts


def generate_appointments_and_shipments(
    facilities: List[dict],
    docks: List[dict],
    yard_slots: List[dict],
    carriers: List[dict],
    vehicles: List[dict],
    labor_shifts: List[dict],
    n_appointments: int,
    rng: random.Random,
) -> Tuple[List[dict], List[dict], List[dict]]:
    """
    Generate valid baseline appointments + shipments + handling requirements.
    Capacity and compatibility are respected for the baseline set.
    Edge cases are injected later.
    """
    # index helpers
    docks_by_fac: Dict[str, List[dict]] = {}
    for d in docks:
        docks_by_fac.setdefault(d["facility_id"], []).append(d)

    slots_by_dock: Dict[str, List[dict]] = {}
    for s in yard_slots:
        slots_by_dock.setdefault(s["dock_id"], []).append(s)

    vehicles_by_carrier: Dict[str, List[dict]] = {}
    for v in vehicles:
        vehicles_by_carrier.setdefault(v["carrier_id"], []).append(v)

    # capacity tracker: dock_id → date → count
    capacity_used: Dict[str, Dict[str, int]] = {}
    for d in docks:
        capacity_used[d["dock_id"]] = {}

    appointments = []
    shipments = []
    handling_reqs = []

    appt_counter = 0
    attempts = 0
    max_attempts = n_appointments * 8

    while appt_counter < n_appointments and attempts < max_attempts:
        attempts += 1
        fac = rng.choice(facilities)
        dock_list = docks_by_fac.get(fac["facility_id"], [])
        if not dock_list:
            continue
        dock = rng.choice(dock_list)
        carrier = rng.choice(carriers)
        veh_list = vehicles_by_carrier.get(carrier["carrier_id"], [])
        if not veh_list:
            continue
        vehicle = rng.choice(veh_list)

        # choose handling type consistent with vehicle / dock when possible
        if vehicle["vehicle_type"] == "REEFER" or dock["dock_type"] == "REFRIGERATED":
            handling = "REFRIGERATED"
        elif vehicle["vehicle_type"] == "TANKER" or dock["dock_type"] == "HAZMAT":
            handling = "HAZARDOUS"
        elif vehicle["vehicle_type"] == "FLATBED" or dock["dock_type"] == "OVERSIZE":
            handling = "OVERSIZE"
        else:
            handling = rng.choice(HANDLING_TYPES)

        if not is_compatible(vehicle["vehicle_type"], dock["dock_type"], handling):
            # try a different dock of the same facility
            compatible_docks = [
                d for d in dock_list
                if is_compatible(vehicle["vehicle_type"], d["dock_type"], handling)
            ]
            if not compatible_docks:
                continue
            dock = rng.choice(compatible_docks)

        # pick a date with remaining capacity
        day_offset = rng.randint(0, HORIZON_DAYS - 1)
        target_date = (START_DATE + timedelta(days=day_offset)).isoformat()
        used = capacity_used[dock["dock_id"]].get(target_date, 0)
        if used >= dock["daily_capacity"]:
            continue

        # window
        open_h = int(fac["open_time"][:2])
        close_h = int(fac["close_time"][:2])
        window_start_h = rng.randint(open_h, max(open_h, close_h - 3))
        window_start = f"{window_start_h:02d}:00"
        window_end = f"{min(window_start_h + 2, close_h):02d}:00"

        weight = round(rng.uniform(2000, 22000), 0)
        is_ref = handling == "REFRIGERATED"
        is_haz = handling == "HAZARDOUS"
        is_over = handling == "OVERSIZE"
        duration = service_duration_minutes(handling, weight, is_over)

        appt_counter += 1
        appt_id = f"APPT-2026-{appt_counter:06d}"
        shp_id = f"SHP-2026-{appt_counter:06d}"

        # yard slot (optional – 70 % assigned)
        ys_list = slots_by_dock.get(dock["dock_id"], [])
        yard_slot_id = rng.choice(ys_list)["yard_slot_id"] if ys_list and rng.random() > 0.3 else None

        status = "CONFIRMED" if rng.random() > 0.15 else "REQUESTED"
        confirmed_date = target_date if status == "CONFIRMED" else None
        confirmed_start = window_start if status == "CONFIRMED" else None
        confirmed_end = window_end if status == "CONFIRMED" else None

        now_iso = datetime(2026, 8, 15, 10, 0, 0).isoformat()

        appt = Appointment(
            appointment_id=appt_id,
            facility_id=fac["facility_id"],
            dock_id=dock["dock_id"],
            yard_slot_id=yard_slot_id,
            carrier_id=carrier["carrier_id"],
            vehicle_id=vehicle["vehicle_id"],
            shipment_id=shp_id,
            appointment_type=rng.choice(APPOINTMENT_TYPES),
            requested_date=target_date,
            requested_window_start=window_start,
            requested_window_end=window_end,
            confirmed_date=confirmed_date,
            confirmed_window_start=confirmed_start,
            confirmed_window_end=confirmed_end,
            status=status,
            service_duration_min=duration,
            created_at=now_iso,
            updated_at=now_iso,
        )
        appointments.append(to_dict(appt))

        shp = Shipment(
            shipment_id=shp_id,
            appointment_id=appt_id,
            carrier_id=carrier["carrier_id"],
            vehicle_id=vehicle["vehicle_id"],
            direction=appt.appointment_type,
            weight_kg=weight,
            volume_cbm=round(rng.uniform(10, 70), 1),
            commodity=rng.choice(COMMODITIES),
            is_refrigerated=is_ref,
            is_hazardous=is_haz,
            is_oversize=is_over,
            origin=f"{rng.choice(['Dallas','Atlanta','Chicago','LA'])}, USA",
            destination=f"{fac['city']}, {fac['state']}",
        )
        shipments.append(to_dict(shp))

        hr = HandlingRequirement(
            handling_req_id=f"HR-{appt_counter:06d}",
            shipment_id=shp_id,
            handling_type=handling,
            temperature_min_c=-18.0 if is_ref else None,
            temperature_max_c=-15.0 if is_ref else None,
            hazmat_class="3" if is_haz else None,
            special_equipment="LEVELER" if rng.random() > 0.6 else None,
            service_duration_min=duration,
        )
        handling_reqs.append(to_dict(hr))

        # book capacity
        capacity_used[dock["dock_id"]][target_date] = used + 1

    return appointments, shipments, handling_reqs
