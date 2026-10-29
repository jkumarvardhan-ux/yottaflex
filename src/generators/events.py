"""
Event simulation: CheckInEvent lifecycle for each appointment.
History is append-only; status changes are recorded as events.
"""

from __future__ import annotations
import random
from datetime import datetime, timedelta, date
from typing import List, Dict, Tuple

from ..models import CheckInEvent, to_dict
from ..business_rules import legal_transition


def _parse_date(d: str) -> date:
    return date.fromisoformat(d)


def _make_ts(base_date: str, hour: int, minute: int = 0) -> str:
    d = _parse_date(base_date)
    return datetime(d.year, d.month, d.day, hour, minute, 0).isoformat()


def generate_events_for_appointment(
    appt: dict,
    rng: random.Random,
    inject_no_show: bool = False,
    inject_early: bool = False,
    inject_congestion: bool = False,
) -> Tuple[List[dict], str]:
    """
    Simulate a realistic event chain for one appointment.
    Returns (list_of_events, final_status).
    """
    events = []
    appt_id = appt["appointment_id"]
    seq = 0
    final_status = appt["status"]

    if appt["status"] in ("REQUESTED", "CANCELLED"):
        return events, final_status

    target_date = appt.get("confirmed_date") or appt["requested_date"]
    window_start_h = int((appt.get("confirmed_window_start") or appt["requested_window_start"])[:2])

    # ---- NO-SHOW path ----
    if inject_no_show or (rng.random() < 0.04 and appt["status"] == "CONFIRMED"):
        seq += 1
        events.append(to_dict(CheckInEvent(
            event_id=f"CHECK-{appt_id}-{seq:02d}",
            appointment_id=appt_id,
            facility_id=appt["facility_id"],
            dock_id=appt["dock_id"],
            event_type="NO_SHOW",
            event_ts=_make_ts(target_date, window_start_h + 2),
            sequence=seq,
            actor_role="SYSTEM",
            notes="Carrier did not arrive within window",
        )))
        return events, "NO_SHOW"

    # ---- CHECK-IN ----
    arrive_h = window_start_h
    arrive_m = rng.randint(0, 25)
    if inject_early:
        arrive_h = max(0, window_start_h - 1)
        arrive_m = rng.randint(30, 55)

    seq += 1
    checkin_ts = _make_ts(target_date, arrive_h, arrive_m)
    events.append(to_dict(CheckInEvent(
        event_id=f"CHECK-{appt_id}-{seq:02d}",
        appointment_id=appt_id,
        facility_id=appt["facility_id"],
        dock_id=appt["dock_id"],
        event_type="CHECK_IN",
        event_ts=checkin_ts,
        sequence=seq,
        actor_role="WAREHOUSE_OPERATOR",
        notes="Early arrival" if inject_early else None,
        wait_time_min=0,
    )))
    final_status = "CHECKED_IN"

    # optional congestion delay
    delay_min = 0
    if inject_congestion or rng.random() < 0.08:
        delay_min = rng.randint(15, 45)
        seq += 1
        events.append(to_dict(CheckInEvent(
            event_id=f"CHECK-{appt_id}-{seq:02d}",
            appointment_id=appt_id,
            facility_id=appt["facility_id"],
            dock_id=appt["dock_id"],
            event_type="CONGESTION_DELAY",
            event_ts=(datetime.fromisoformat(checkin_ts) + timedelta(minutes=5)).isoformat(),
            sequence=seq,
            actor_role="SYSTEM",
            notes=f"Yard congestion – estimated delay {delay_min} min",
            wait_time_min=delay_min,
        )))

    # ---- LOADING / UNLOADING ----
    direction = appt["appointment_type"]
    start_type = "UNLOADING_START" if direction == "INBOUND" else "LOADING_START"
    end_type = "UNLOADING_END" if direction == "INBOUND" else "LOADING_END"

    service_min = appt.get("service_duration_min", 60)
    load_start = datetime.fromisoformat(checkin_ts) + timedelta(minutes=10 + delay_min)
    load_end = load_start + timedelta(minutes=service_min)

    seq += 1
    events.append(to_dict(CheckInEvent(
        event_id=f"CHECK-{appt_id}-{seq:02d}",
        appointment_id=appt_id,
        facility_id=appt["facility_id"],
        dock_id=appt["dock_id"],
        event_type=start_type,
        event_ts=load_start.isoformat(),
        sequence=seq,
        actor_role="DOCK_WORKER",
        wait_time_min=10 + delay_min,
    )))
    final_status = "LOADING"

    seq += 1
    events.append(to_dict(CheckInEvent(
        event_id=f"CHECK-{appt_id}-{seq:02d}",
        appointment_id=appt_id,
        facility_id=appt["facility_id"],
        dock_id=appt["dock_id"],
        event_type=end_type,
        event_ts=load_end.isoformat(),
        sequence=seq,
        actor_role="DOCK_WORKER",
        dwell_time_min=service_min,
    )))

    # ---- DEPARTURE ----
    depart = load_end + timedelta(minutes=rng.randint(5, 20))
    seq += 1
    events.append(to_dict(CheckInEvent(
        event_id=f"CHECK-{appt_id}-{seq:02d}",
        appointment_id=appt_id,
        facility_id=appt["facility_id"],
        dock_id=appt["dock_id"],
        event_type="DEPARTURE",
        event_ts=depart.isoformat(),
        sequence=seq,
        actor_role="WAREHOUSE_OPERATOR",
        dwell_time_min=int((depart - datetime.fromisoformat(checkin_ts)).total_seconds() / 60),
    )))
    final_status = "DEPARTED"

    return events, final_status


def generate_all_events(
    appointments: List[dict],
    rng: random.Random,
) -> Tuple[List[dict], List[dict]]:
    """
    Generate events for every confirmed (or later) appointment.
    Also updates appointment status in-place and returns the updated list.
    """
    all_events = []
    updated_appts = []

    for appt in appointments:
        # decide injection flags for normal path (edge cases handled separately)
        inject_no_show = False
        inject_early = rng.random() < 0.06
        inject_congestion = rng.random() < 0.07

        events, final_status = generate_events_for_appointment(
            appt, rng,
            inject_no_show=inject_no_show,
            inject_early=inject_early,
            inject_congestion=inject_congestion,
        )
        all_events.extend(events)

        # update status (history is in events; we still keep current status)
        new_appt = dict(appt)
        if final_status != appt["status"] and appt["status"] not in ("REQUESTED", "CANCELLED"):
            new_appt["status"] = final_status
            new_appt["updated_at"] = events[-1]["event_ts"] if events else appt["updated_at"]
        updated_appts.append(new_appt)

    return all_events, updated_appts
