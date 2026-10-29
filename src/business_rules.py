"""
Business rules engine for dock/yard capacity, compatibility and service durations.
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, date, time, timedelta
from collections import defaultdict

from .config import (
    DOCK_DAILY_CAPACITY,
    SERVICE_DURATION_BASE_MIN,
    COMPATIBILITY,
    HANDLING_TYPES,
)


def dock_capacity(dock_type: str) -> int:
    return DOCK_DAILY_CAPACITY.get(dock_type, 6)


def is_compatible(vehicle_type: str, dock_type: str, handling_type: str) -> bool:
    """Return True if vehicle can use the dock for the given handling requirement."""
    allowed_docks = COMPATIBILITY.get(vehicle_type, [])
    if dock_type not in allowed_docks:
        return False
    # Extra constraints
    if handling_type == "HAZARDOUS" and dock_type != "HAZMAT":
        return False
    if handling_type == "REFRIGERATED" and dock_type not in ("REFRIGERATED", "STANDARD"):
        return False
    if handling_type == "OVERSIZE" and dock_type not in ("OVERSIZE", "STANDARD"):
        return False
    return True


def service_duration_minutes(
    handling_type: str,
    weight_kg: float,
    is_oversize: bool = False,
) -> int:
    """Deterministic service duration from handling type + weight."""
    base = SERVICE_DURATION_BASE_MIN.get(handling_type, 45)
    # +5 min per 2 000 kg above 5 000 kg
    extra = max(0, int((weight_kg - 5000) / 2000)) * 5
    if is_oversize:
        extra += 30
    return base + extra


def build_capacity_calendar(
    docks: List[dict],
    appointments: List[dict],
    horizon_start: date,
    horizon_days: int,
) -> Dict[str, Dict[str, int]]:
    """
    Returns {dock_id: {date_iso: booked_count}}.
    Used both for generation and for validation.
    """
    calendar: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for appt in appointments:
        if appt["status"] in ("CANCELLED", "NO_SHOW"):
            continue
        d = appt.get("confirmed_date") or appt.get("requested_date")
        if d:
            calendar[appt["dock_id"]][d] += 1
    return calendar


def capacity_exceeded(
    dock_id: str,
    dock_type: str,
    target_date: str,
    calendar: Dict[str, Dict[str, int]],
) -> bool:
    booked = calendar.get(dock_id, {}).get(target_date, 0)
    return booked >= dock_capacity(dock_type)


def labor_available(
    facility_id: str,
    target_date: str,
    window_start: str,
    labor_shifts: List[dict],
) -> bool:
    """Simple check: at least one available shift covering the window on that date."""
    for ls in labor_shifts:
        if (
            ls["facility_id"] == facility_id
            and ls["shift_date"] == target_date
            and ls["is_available"]
        ):
            # crude time overlap – sufficient for synthetic data
            if ls["start_time"] <= window_start <= ls["end_time"]:
                return True
    return False


def legal_transition(from_status: str, to_status: str) -> bool:
    """Finite-state machine for appointment lifecycle."""
    allowed = {
        "REQUESTED": {"CONFIRMED", "CANCELLED"},
        "CONFIRMED": {"CHECKED_IN", "NO_SHOW", "CANCELLED"},
        "CHECKED_IN": {"LOADING", "CANCELLED"},
        "LOADING": {"DEPARTED", "CANCELLED"},
        "DEPARTED": set(),
        "NO_SHOW": set(),
        "CANCELLED": set(),
    }
    return to_status in allowed.get(from_status, set())


def compute_utilization(
    dock_id: str,
    dock_type: str,
    calendar: Dict[str, Dict[str, int]],
    horizon_days: int,
) -> float:
    """Average daily utilization (booked / capacity) over the horizon."""
    cap = dock_capacity(dock_type)
    if cap == 0:
        return 0.0
    daily = calendar.get(dock_id, {})
    if not daily:
        return 0.0
    total_booked = sum(daily.values())
    return round(total_booked / (cap * horizon_days), 4)


def compute_wait_time(events: List[dict], appointment_id: str) -> Optional[int]:
    """Wait time = minutes between first CHECK_IN and first LOADING/UNLOADING event."""
    appt_events = sorted(
        [e for e in events if e["appointment_id"] == appointment_id],
        key=lambda e: (e["sequence"], e["event_ts"]),
    )
    checkin_ts = None
    load_ts = None
    for e in appt_events:
        if e["event_type"] == "CHECK_IN" and checkin_ts is None:
            checkin_ts = e["event_ts"]
        if e["event_type"] in ("LOADING_START", "UNLOADING_START") and load_ts is None:
            load_ts = e["event_ts"]
    if checkin_ts and load_ts:
        t0 = datetime.fromisoformat(checkin_ts)
        t1 = datetime.fromisoformat(load_ts)
        return max(0, int((t1 - t0).total_seconds() / 60))
    return None
