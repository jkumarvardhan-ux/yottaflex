"""
Master data generators: Facility, Dock, YardSlot, Carrier, Vehicle.
IDs are deterministic given the RNG seed.
"""

from __future__ import annotations
import random
from typing import List, Dict, Tuple

from ..config import (
    FACILITY_TYPES,
    DOCK_TYPES,
    VEHICLE_TYPES,
    DOCK_DAILY_CAPACITY,
)
from ..models import Facility, Dock, YardSlot, Carrier, Vehicle, to_dict


CITIES = [
    ("Dallas", "TX"), ("Atlanta", "GA"), ("Chicago", "IL"), ("Los Angeles", "CA"),
    ("Newark", "NJ"), ("Houston", "TX"), ("Memphis", "TN"), ("Columbus", "OH"),
    ("Phoenix", "AZ"), ("Seattle", "WA"), ("Denver", "CO"), ("Miami", "FL"),
]

CARRIER_NAMES = [
    "Swift Logistics", "JB Hunt", "Schneider National", "Werner Enterprises",
    "Knight-Swift", "Old Dominion", "XPO Logistics", "Ryder", "Penske",
    "C.H. Robinson", "Landstar", "Estes Express", "Saia", "YRC Worldwide",
    "FedEx Freight", "UPS Freight", "TForce", "Dayton Freight", "R+L Carriers",
    "Southeastern Freight", "AAA Cooper", "Pitt Ohio", "A. Duie Pyle",
    "Holland", "Reddaway", "New Penn", "ABF Freight", "Central Transport",
    "Roadrunner", "Forward Air", "Echo Global", "Mode Transportation",
    "Total Quality Logistics", "Hub Group", "J.B. Hunt Intermodal",
    "Schneider Intermodal", "Swift Intermodal", "Werner Intermodal",
    "Knight Transportation", "U.S. Xpress",
]


def generate_facilities(n: int, rng: random.Random) -> List[dict]:
    facilities = []
    for i in range(1, n + 1):
        fid = f"FAC-{i:03d}"
        city, state = CITIES[(i - 1) % len(CITIES)]
        ftype = FACILITY_TYPES[(i - 1) % len(FACILITY_TYPES)]
        open_h = 5 + (i % 3)          # 05:00 – 07:00
        close_h = 20 + (i % 3)        # 20:00 – 22:00
        fac = Facility(
            facility_id=fid,
            name=f"{city} {ftype.replace('_', ' ').title()} #{i}",
            facility_type=ftype,
            city=city,
            state=state,
            country="USA",
            timezone="America/Chicago" if state in ("TX", "IL", "TN") else "America/New_York",
            open_time=f"{open_h:02d}:00",
            close_time=f"{close_h:02d}:00",
            is_active=True,
            effective_from="2026-01-01",
            effective_to=None,
        )
        facilities.append(to_dict(fac))
    return facilities


def generate_docks(facilities: List[dict], docks_per_facility: int, rng: random.Random) -> List[dict]:
    docks = []
    for fac in facilities:
        for d in range(1, docks_per_facility + 1):
            dock_type = DOCK_TYPES[(d - 1) % len(DOCK_TYPES)]
            # bias refrigerated / hazmat for cold-storage / hazmat facilities
            if fac["facility_type"] == "COLD_STORAGE" and d % 2 == 0:
                dock_type = "REFRIGERATED"
            if fac["facility_type"] == "HAZMAT_DEPOT" and d % 2 == 0:
                dock_type = "HAZMAT"
            dock_id = f"DOCK-{fac['facility_id']}-{d:03d}"
            dock = Dock(
                dock_id=dock_id,
                facility_id=fac["facility_id"],
                dock_number=d,
                dock_type=dock_type,
                max_vehicle_length_m=round(12.0 + rng.uniform(0, 6), 1),
                has_leveler=rng.random() > 0.15,
                has_reefer_hookup=dock_type == "REFRIGERATED" or rng.random() > 0.7,
                has_hazmat_cert=dock_type == "HAZMAT" or rng.random() > 0.85,
                daily_capacity=DOCK_DAILY_CAPACITY[dock_type],
                is_active=True,
            )
            docks.append(to_dict(dock))
    return docks


def generate_yard_slots(docks: List[dict], slots_per_dock: int = 2) -> List[dict]:
    slots = []
    for dock in docks:
        for s in range(1, slots_per_dock + 1):
            ys_id = f"YS-{dock['dock_id']}-{s:02d}"
            slot = YardSlot(
                yard_slot_id=ys_id,
                dock_id=dock["dock_id"],
                facility_id=dock["facility_id"],
                slot_number=s,
                max_dwell_hours=round(4.0 + (s * 0.5), 1),
                is_covered=s == 1,
                is_active=True,
            )
            slots.append(to_dict(slot))
    return slots


def generate_carriers(n: int, rng: random.Random) -> List[dict]:
    carriers = []
    used_names = set()
    for i in range(1, n + 1):
        cid = f"CAR-{i:04d}"
        name = CARRIER_NAMES[(i - 1) % len(CARRIER_NAMES)]
        if name in used_names:
            name = f"{name} {i}"
        used_names.add(name)
        scac = "".join(rng.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=4))
        car = Carrier(
            carrier_id=cid,
            name=name,
            scac=scac,
            contact_email=f"ops@{name.lower().replace(' ', '').replace('.', '')[:12]}.com",
            is_preferred=rng.random() > 0.6,
            is_active=True,
        )
        carriers.append(to_dict(car))
    return carriers


def generate_vehicles(
    carriers: List[dict],
    vehicles_per_carrier: int,
    rng: random.Random,
) -> List[dict]:
    vehicles = []
    for car in carriers:
        for v in range(1, vehicles_per_carrier + 1):
            vid = f"VEH-{car['carrier_id']}-{v:03d}"
            vtype = VEHICLE_TYPES[(v - 1) % len(VEHICLE_TYPES)]
            has_reefer = vtype == "REEFER" or (vtype == "DRY_VAN" and rng.random() > 0.85)
            has_hazmat = vtype == "TANKER" or rng.random() > 0.9
            veh = Vehicle(
                vehicle_id=vid,
                carrier_id=car["carrier_id"],
                vehicle_type=vtype,
                license_plate=f"{rng.choice('ABCDEFGHJKLMNPRSTUVWXYZ')}{rng.randint(100,999)}"
                              f"{rng.choice('ABCDEFGHJKLMNPRSTUVWXYZ')}{rng.randint(10,99)}",
                max_weight_kg=round(rng.uniform(8000, 25000), 0),
                length_m=round(rng.uniform(8.0, 16.0), 1),
                has_reefer=has_reefer,
                has_hazmat_cert=has_hazmat,
                is_active=True,
            )
            vehicles.append(to_dict(veh))
    return vehicles
