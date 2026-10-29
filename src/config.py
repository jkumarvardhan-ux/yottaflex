"""
Configuration, volumes and constants for the YottaFlex synthetic data generator.
All generation is deterministic given the seed.
"""

from pathlib import Path
from datetime import date, timedelta

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
CSV_DIR = DATA_DIR / "csv"
JSON_DIR = DATA_DIR / "json"
DOCS_DIR = ROOT / "docs"

# ---------------------------------------------------------------------------
# Seed & time horizon
# ---------------------------------------------------------------------------
DEFAULT_SEED = 20261022
START_DATE = date(2026, 9, 1)          # start of the 60-day window
HORIZON_DAYS = 60
END_DATE = START_DATE + timedelta(days=HORIZON_DAYS - 1)

# ---------------------------------------------------------------------------
# Volume profiles
# ---------------------------------------------------------------------------
VOLUMES = {
    "starter": {
        "n_facilities": 3,
        "n_docks_per_facility": 4,          # ~12 docks
        "n_carriers": 8,
        "n_vehicles_per_carrier": 3,
        "n_appointments": 400,
        "n_labor_shifts_per_facility_day": 2,
        "edge_case_fraction": 0.08,
    },
    "full": {
        "n_facilities": 10,
        "n_docks_per_facility": 10,         # 100 docks
        "n_carriers": 40,
        "n_vehicles_per_carrier": 5,
        "n_appointments": 20_000,
        "n_labor_shifts_per_facility_day": 3,
        "edge_case_fraction": 0.05,
    },
}

# ---------------------------------------------------------------------------
# Domain constants
# ---------------------------------------------------------------------------
FACILITY_TYPES = ["DISTRIBUTION_CENTER", "CROSS_DOCK", "COLD_STORAGE", "HAZMAT_DEPOT"]
DOCK_TYPES = ["STANDARD", "REFRIGERATED", "HAZMAT", "OVERSIZE"]
VEHICLE_TYPES = ["DRY_VAN", "REEFER", "TANKER", "FLATBED", "BOX_TRUCK"]
HANDLING_TYPES = ["STANDARD", "REFRIGERATED", "HAZARDOUS", "OVERSIZE"]
APPOINTMENT_TYPES = ["INBOUND", "OUTBOUND"]
APPOINTMENT_STATUSES = [
    "REQUESTED",
    "CONFIRMED",
    "CHECKED_IN",
    "LOADING",
    "DEPARTED",
    "NO_SHOW",
    "CANCELLED",
]
EVENT_TYPES = [
    "CHECK_IN",
    "UNLOADING_START",
    "UNLOADING_END",
    "LOADING_START",
    "LOADING_END",
    "DEPARTURE",
    "NO_SHOW",
    "EARLY_ARRIVAL",
    "CONGESTION_DELAY",
]
EXCEPTION_TYPES = [
    "CAPACITY_EXCEEDED",
    "INCOMPATIBLE_LOAD",
    "CHECKIN_BEFORE_WINDOW",
    "LABOR_UNAVAILABLE",
    "NO_SHOW_UNRECORDED",
    "OVERLAPPING_SLOT",
]
SEVERITY = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]

# Dock capacity (appointments per day) by dock type
DOCK_DAILY_CAPACITY = {
    "STANDARD": 8,
    "REFRIGERATED": 6,
    "HAZMAT": 4,
    "OVERSIZE": 3,
}

# Service duration base minutes by handling type
SERVICE_DURATION_BASE_MIN = {
    "STANDARD": 45,
    "REFRIGERATED": 60,
    "HAZARDOUS": 90,
    "OVERSIZE": 120,
}

# Compatible vehicle ↔ dock / handling
COMPATIBILITY = {
    # vehicle_type → allowed dock_types
    "DRY_VAN": ["STANDARD", "OVERSIZE"],
    "REEFER": ["REFRIGERATED", "STANDARD"],
    "TANKER": ["HAZMAT"],
    "FLATBED": ["OVERSIZE", "STANDARD"],
    "BOX_TRUCK": ["STANDARD"],
}

# Labor roles
LABOR_ROLES = ["DOCK_WORKER", "FORKLIFT_OPERATOR", "SUPERVISOR", "HAZMAT_CERTIFIED"]
