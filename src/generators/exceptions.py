"""
Labelled edge-case / anomaly injection.
Each injected anomaly receives a ground-truth row; the anomaly itself appears
in the operational tables so that downstream models can be evaluated.
"""

from __future__ import annotations
import random
from datetime import datetime, timedelta, date
from typing import List, Dict, Tuple

from ..models import ExceptionRecord, GroundTruth, CheckInEvent, to_dict
from ..business_rules import is_compatible, dock_capacity
from ..config import EXCEPTION_TYPES, SEVERITY


def _make_ts(base_date: str, hour: int, minute: int = 0) -> str:
    d = date.fromisoformat(base_date)
    return datetime(d.year, d.month, d.day, hour, minute, 0).isoformat()


def inject_edge_cases(
    appointments: List[dict],
    docks: List[dict],
    vehicles: List[dict],
    labor_shifts: List[dict],
    events: List[dict],
    fraction: float,
    rng: random.Random,
) -> Tuple[List[dict], List[dict], List[dict], List[dict]]:
    """
    Inject labelled edge cases into a copy of the data.
    Returns:
        updated_appointments,
        extra_events,
        exception_records,
        ground_truth_rows
    """
    n_inject = max(5, int(len(appointments) * fraction))
    candidates = [a for a in appointments if a["status"] in ("CONFIRMED", "CHECKED_IN", "DEPARTED", "REQUESTED")]
    if not candidates:
        return appointments, [], [], []

    to_mutate = rng.sample(candidates, min(n_inject, len(candidates)))
    dock_by_id = {d["dock_id"]: d for d in docks}
    vehicle_by_id = {v["vehicle_id"]: v for v in vehicles}

    extra_events = []
    exceptions = []
    ground_truth = []
    appt_map = {a["appointment_id"]: dict(a) for a in appointments}

    issue_cycle = [
        "CAPACITY_EXCEEDED",
        "INCOMPATIBLE_LOAD",
        "CHECKIN_BEFORE_WINDOW",
        "LABOR_UNAVAILABLE",
        "NO_SHOW_UNRECORDED",
    ]

    for idx, appt in enumerate(to_mutate):
        issue = issue_cycle[idx % len(issue_cycle)]
        appt_id = appt["appointment_id"]
        dock = dock_by_id.get(appt["dock_id"], {})
        vehicle = vehicle_by_id.get(appt["vehicle_id"], {})
        target_date = appt.get("confirmed_date") or appt["requested_date"]
        window_start_h = int((appt.get("confirmed_window_start") or appt["requested_window_start"])[:2])

        exc_id = f"EXC-{idx + 1:06d}"
        gt_id = f"GT-{idx + 1:06d}"
        now = datetime(2026, 10, 1, 12, 0, 0).isoformat()

        if issue == "CAPACITY_EXCEEDED":
            # force status to CONFIRMED even though capacity would be exceeded
            # (we just mark it; the calendar already has normal bookings)
            appt_map[appt_id]["status"] = "CONFIRMED"
            appt_map[appt_id]["notes"] = "FORCE_CAPACITY_OVERFLOW"
            desc = f"Appointment {appt_id} confirmed on dock {appt['dock_id']} exceeding daily capacity"
            expected = "REJECT_OR_RESCHEDULE"
            severity = "HIGH"

        elif issue == "INCOMPATIBLE_LOAD":
            # change dock to an incompatible one (keep vehicle)
            # find any dock of different type
            other_docks = [d for d in docks if d["dock_id"] != appt["dock_id"]]
            if other_docks:
                bad_dock = rng.choice(other_docks)
                appt_map[appt_id]["dock_id"] = bad_dock["dock_id"]
                appt_map[appt_id]["facility_id"] = bad_dock["facility_id"]
            desc = f"Incompatible vehicle/dock pairing for {appt_id}"
            expected = "REJECT_INCOMPATIBLE"
            severity = "CRITICAL"

        elif issue == "CHECKIN_BEFORE_WINDOW":
            # add a check-in event one day early (high sequence to avoid collision)
            early_date = (date.fromisoformat(target_date) - timedelta(days=1)).isoformat()
            seq = 90  # high number so it does not collide with normal 1..N sequences
            extra_events.append(to_dict(CheckInEvent(
                event_id=f"CHECK-{appt_id}-E{seq:02d}",
                appointment_id=appt_id,
                facility_id=appt["facility_id"],
                dock_id=appt["dock_id"],
                event_type="CHECK_IN",
                event_ts=_make_ts(early_date, window_start_h),
                sequence=seq,
                actor_role="WAREHOUSE_OPERATOR",
                notes="CHECKIN_BEFORE_APPOINTMENT_DATE",
            )))
            appt_map[appt_id]["status"] = "CHECKED_IN"
            desc = f"Check-in recorded before appointment date for {appt_id}"
            expected = "FLAG_EARLY_CHECKIN"
            severity = "MEDIUM"

        elif issue == "LABOR_UNAVAILABLE":
            # mark the appointment as confirmed on a date/time with no labor
            # (we simply flag it; validation will surface the gap)
            appt_map[appt_id]["status"] = "CONFIRMED"
            appt_map[appt_id]["notes"] = "NO_LABOR_SHIFT"
            desc = f"No matching labor shift for {appt_id} on {target_date}"
            expected = "BLOCK_OR_ESCALATE"
            severity = "HIGH"

        elif issue == "NO_SHOW_UNRECORDED":
            # appointment stays CONFIRMED but no NO_SHOW event is written
            appt_map[appt_id]["status"] = "CONFIRMED"
            appt_map[appt_id]["notes"] = "MISSING_NO_SHOW_EVENT"
            desc = f"Expected NO_SHOW event missing for {appt_id}"
            expected = "RECORD_NO_SHOW"
            severity = "MEDIUM"

        else:
            continue

        exceptions.append(to_dict(ExceptionRecord(
            exception_id=exc_id,
            entity_type="Appointment",
            entity_id=appt_id,
            issue_type=issue,
            severity=severity,
            detected_at=now,
            description=desc,
            cause_code=issue,
            resolved=False,
        )))

        ground_truth.append(to_dict(GroundTruth(
            gt_id=gt_id,
            entity_type="Appointment",
            entity_id=appt_id,
            issue_type=issue,
            expected_label=issue,
            expected_decision=expected,
            rule_reference=f"BR-{issue}",
            severity=severity,
            injected=True,
        )))

    updated_appts = list(appt_map.values())
    return updated_appts, extra_events, exceptions, ground_truth
