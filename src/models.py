"""
Entity dataclasses for the YottaFlex domain model.
All primary keys follow the documented nomenclature.
"""

from dataclasses import dataclass, field, asdict
from datetime import date, datetime, time
from typing import Optional, List, Dict, Any


def to_dict(obj) -> Dict[str, Any]:
    """Convert dataclass to plain dict (dates → ISO strings)."""
    d = asdict(obj)
    for k, v in d.items():
        if isinstance(v, (date, datetime, time)):
            d[k] = v.isoformat()
        elif v is None:
            d[k] = None
    return d


# ---------------------------------------------------------------------------
# Master data
# ---------------------------------------------------------------------------

@dataclass
class Facility:
    facility_id: str                    # FAC-001
    name: str
    facility_type: str
    city: str
    state: str
    country: str
    timezone: str
    open_time: str                      # "06:00"
    close_time: str                     # "22:00"
    is_active: bool = True
    effective_from: Optional[str] = None
    effective_to: Optional[str] = None


@dataclass
class Dock:
    dock_id: str                        # DOCK-FAC-001-001
    facility_id: str
    dock_number: int
    dock_type: str
    max_vehicle_length_m: float
    has_leveler: bool
    has_reefer_hookup: bool
    has_hazmat_cert: bool
    daily_capacity: int
    is_active: bool = True


@dataclass
class YardSlot:
    yard_slot_id: str                   # YS-DOCK-FAC-001-001-01
    dock_id: str
    facility_id: str
    slot_number: int
    max_dwell_hours: float
    is_covered: bool
    is_active: bool = True


@dataclass
class Carrier:
    carrier_id: str                     # CAR-0001
    name: str
    scac: str
    contact_email: str
    is_preferred: bool
    is_active: bool = True


@dataclass
class Vehicle:
    vehicle_id: str                     # VEH-CAR-0001-001
    carrier_id: str
    vehicle_type: str
    license_plate: str
    max_weight_kg: float
    length_m: float
    has_reefer: bool
    has_hazmat_cert: bool
    is_active: bool = True


# ---------------------------------------------------------------------------
# Transactional
# ---------------------------------------------------------------------------

@dataclass
class LaborShift:
    labor_shift_id: str                 # LS-FAC-001-20260901-01
    facility_id: str
    shift_date: str                     # ISO date
    start_time: str
    end_time: str
    role: str
    headcount: int
    is_available: bool = True


@dataclass
class HandlingRequirement:
    handling_req_id: str                # HR-000001
    shipment_id: str
    handling_type: str
    temperature_min_c: Optional[float]
    temperature_max_c: Optional[float]
    hazmat_class: Optional[str]
    special_equipment: Optional[str]
    service_duration_min: int


@dataclass
class Shipment:
    shipment_id: str                    # SHP-2026-000001
    appointment_id: str
    carrier_id: str
    vehicle_id: str
    direction: str                      # INBOUND / OUTBOUND
    weight_kg: float
    volume_cbm: float
    commodity: str
    is_refrigerated: bool
    is_hazardous: bool
    is_oversize: bool
    origin: str
    destination: str


@dataclass
class Appointment:
    appointment_id: str                 # APPT-2026-000001
    facility_id: str
    dock_id: str
    yard_slot_id: Optional[str]
    carrier_id: str
    vehicle_id: str
    shipment_id: str
    appointment_type: str               # INBOUND / OUTBOUND
    requested_date: str
    requested_window_start: str         # "08:00"
    requested_window_end: str
    confirmed_date: Optional[str]
    confirmed_window_start: Optional[str]
    confirmed_window_end: Optional[str]
    status: str
    service_duration_min: int
    created_at: str
    updated_at: str


# ---------------------------------------------------------------------------
# Events & Exceptions
# ---------------------------------------------------------------------------

@dataclass
class CheckInEvent:
    event_id: str                       # CHECK-APPT-2026-000001-01
    appointment_id: str
    facility_id: str
    dock_id: str
    event_type: str
    event_ts: str                       # ISO datetime
    sequence: int
    actor_role: str
    notes: Optional[str] = None
    wait_time_min: Optional[int] = None
    dwell_time_min: Optional[int] = None


@dataclass
class ExceptionRecord:
    exception_id: str                   # EXC-000001
    entity_type: str                    # Appointment / CheckInEvent / …
    entity_id: str
    issue_type: str
    severity: str
    detected_at: str
    description: str
    cause_code: str
    resolved: bool = False
    resolution_notes: Optional[str] = None


@dataclass
class GroundTruth:
    gt_id: str
    entity_type: str
    entity_id: str
    issue_type: str
    expected_label: str
    expected_decision: str
    rule_reference: str
    severity: str
    injected: bool = True
