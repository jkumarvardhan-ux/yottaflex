# Data Dictionary – YottaFlex Dock & Yard Appointment Scheduler

All fields are documented with type, required/optional, allowed values, units, uniqueness and validation rules.

---

## 1. Facility

| Field            | Type      | Required | Allowed / Notes                          | Unique |
|------------------|-----------|----------|------------------------------------------|--------|
| facility_id      | string    | yes      | `FAC-XXX`                                | PK     |
| name             | string    | yes      | free text                                |        |
| facility_type    | enum      | yes      | DISTRIBUTION_CENTER, CROSS_DOCK, COLD_STORAGE, HAZMAT_DEPOT | |
| city             | string    | yes      |                                          |        |
| state            | string    | yes      | US state code                            |        |
| country          | string    | yes      | default USA                              |        |
| timezone         | string    | yes      | IANA tz                                  |        |
| open_time        | string    | yes      | HH:MM                                    |        |
| close_time       | string    | yes      | HH:MM                                    |        |
| is_active        | boolean   | yes      |                                          |        |
| effective_from   | date      | no       | ISO date                                 |        |
| effective_to     | date      | no       | ISO date                                 |        |

**Cardinality**: 1 Facility → N Docks, N LaborShifts, N Appointments.

---

## 2. Dock

| Field                 | Type    | Required | Allowed / Notes                     | Unique |
|-----------------------|---------|----------|-------------------------------------|--------|
| dock_id               | string  | yes      | `DOCK-<facility_id>-XXX`            | PK     |
| facility_id           | string  | yes      | FK → facilities                     |        |
| dock_number           | int     | yes      | 1…N within facility                 |        |
| dock_type             | enum    | yes      | STANDARD, REFRIGERATED, HAZMAT, OVERSIZE | |
| max_vehicle_length_m  | float   | yes      | metres                              |        |
| has_leveler           | boolean | yes      |                                     |        |
| has_reefer_hookup     | boolean | yes      |                                     |        |
| has_hazmat_cert       | boolean | yes      |                                     |        |
| daily_capacity        | int     | yes      | appointments per day                |        |
| is_active             | boolean | yes      |                                     |        |

**Cardinality**: 1 Dock → N YardSlots, N Appointments.

---

## 3. YardSlot

| Field          | Type    | Required | Allowed / Notes                | Unique |
|----------------|---------|----------|--------------------------------|--------|
| yard_slot_id   | string  | yes      | `YS-<dock_id>-XX`              | PK     |
| dock_id        | string  | yes      | FK → docks                     |        |
| facility_id    | string  | yes      | FK → facilities                |        |
| slot_number    | int     | yes      |                                |        |
| max_dwell_hours| float   | yes      | hours                          |        |
| is_covered     | boolean | yes      |                                |        |
| is_active      | boolean | yes      |                                |        |

---

## 4. Carrier

| Field         | Type    | Required | Notes                    | Unique |
|---------------|---------|----------|--------------------------|--------|
| carrier_id    | string  | yes      | `CAR-XXXX`               | PK     |
| name          | string  | yes      |                          |        |
| scac          | string  | yes      | 4-letter SCAC            |        |
| contact_email | string  | yes      |                          |        |
| is_preferred  | boolean | yes      |                          |        |
| is_active     | boolean | yes      |                          |        |

**Cardinality**: 1 Carrier → N Vehicles, N Appointments.

---

## 5. Vehicle

| Field           | Type    | Required | Allowed / Notes                          | Unique |
|-----------------|---------|----------|------------------------------------------|--------|
| vehicle_id      | string  | yes      | `VEH-<carrier_id>-XXX`                   | PK     |
| carrier_id      | string  | yes      | FK → carriers                            |        |
| vehicle_type    | enum    | yes      | DRY_VAN, REEFER, TANKER, FLATBED, BOX_TRUCK | |
| license_plate   | string  | yes      |                                          |        |
| max_weight_kg   | float   | yes      | kg                                       |        |
| length_m        | float   | yes      | metres                                   |        |
| has_reefer      | boolean | yes      |                                          |        |
| has_hazmat_cert | boolean | yes      |                                          |        |
| is_active       | boolean | yes      |                                          |        |

---

## 6. LaborShift

| Field          | Type    | Required | Notes                              | Unique |
|----------------|---------|----------|------------------------------------|--------|
| labor_shift_id | string  | yes      | `LS-<facility>-YYYYMMDD-XX`        | PK     |
| facility_id    | string  | yes      | FK → facilities                    |        |
| shift_date     | date    | yes      | ISO                                |        |
| start_time     | string  | yes      | HH:MM                              |        |
| end_time       | string  | yes      | HH:MM                              |        |
| role           | enum    | yes      | DOCK_WORKER, FORKLIFT_OPERATOR, SUPERVISOR, HAZMAT_CERTIFIED | |
| headcount      | int     | yes      |                                    |        |
| is_available   | boolean | yes      |                                    |        |

---

## 7. Appointment

| Field                   | Type    | Required | Notes                                      | Unique |
|-------------------------|---------|----------|--------------------------------------------|--------|
| appointment_id          | string  | yes      | `APPT-YYYY-NNNNNN`                         | PK     |
| facility_id             | string  | yes      | FK                                         |        |
| dock_id                 | string  | yes      | FK                                         |        |
| yard_slot_id            | string  | no       | FK (optional)                              |        |
| carrier_id              | string  | yes      | FK                                         |        |
| vehicle_id              | string  | yes      | FK                                         |        |
| shipment_id             | string  | yes      | FK → shipments                             |        |
| appointment_type        | enum    | yes      | INBOUND, OUTBOUND                          |        |
| requested_date          | date    | yes      |                                            |        |
| requested_window_start  | string  | yes      | HH:MM                                      |        |
| requested_window_end    | string  | yes      | HH:MM                                      |        |
| confirmed_date          | date    | no       |                                            |        |
| confirmed_window_start  | string  | no       |                                            |        |
| confirmed_window_end    | string  | no       |                                            |        |
| status                  | enum    | yes      | REQUESTED → CONFIRMED → CHECKED_IN → LOADING → DEPARTED / NO_SHOW / CANCELLED | |
| service_duration_min    | int     | yes      | minutes (derived)                          |        |
| created_at              | timestamp | yes    |                                            |        |
| updated_at              | timestamp | yes    |                                            |        |

**Lifecycle**: state transitions are recorded as immutable CheckInEvents; status column reflects current state only.

---

## 8. Shipment

| Field           | Type    | Required | Notes                | Unique |
|-----------------|---------|----------|----------------------|--------|
| shipment_id     | string  | yes      | `SHP-YYYY-NNNNNN`    | PK     |
| appointment_id  | string  | yes      | FK                   |        |
| carrier_id      | string  | yes      |                      |        |
| vehicle_id      | string  | yes      |                      |        |
| direction       | enum    | yes      | INBOUND / OUTBOUND   |        |
| weight_kg       | float   | yes      | kg                   |        |
| volume_cbm      | float   | yes      | m³                   |        |
| commodity       | string  | yes      |                      |        |
| is_refrigerated | boolean | yes      |                      |        |
| is_hazardous    | boolean | yes      |                      |        |
| is_oversize     | boolean | yes      |                      |        |
| origin          | string  | yes      |                      |        |
| destination     | string  | yes      |                      |        |

**Cardinality**: 1 Appointment ↔ 1 Shipment (1:1 in this model).

---

## 9. HandlingRequirement

| Field                | Type    | Required | Notes                          | Unique |
|----------------------|---------|----------|--------------------------------|--------|
| handling_req_id      | string  | yes      | `HR-NNNNNN`                    | PK     |
| shipment_id          | string  | yes      | FK                             |        |
| handling_type        | enum    | yes      | STANDARD, REFRIGERATED, HAZARDOUS, OVERSIZE | |
| temperature_min_c    | float   | no       | °C                             |        |
| temperature_max_c    | float   | no       | °C                             |        |
| hazmat_class         | string  | no       | e.g. “3”                       |        |
| special_equipment    | string  | no       |                                |        |
| service_duration_min | int     | yes      | minutes (derived)              |        |

---

## 10. CheckInEvent

| Field          | Type      | Required | Notes                                      | Unique |
|----------------|-----------|----------|--------------------------------------------|--------|
| event_id       | string    | yes      | `CHECK-<appointment_id>-NN`                | PK     |
| appointment_id | string    | yes      | FK                                         |        |
| facility_id    | string    | yes      |                                            |        |
| dock_id        | string    | yes      |                                            |        |
| event_type     | enum      | yes      | CHECK_IN, UNLOADING_START/END, LOADING_START/END, DEPARTURE, NO_SHOW, EARLY_ARRIVAL, CONGESTION_DELAY | |
| event_ts       | timestamp | yes      | ISO                                        |        |
| sequence       | int       | yes      | 1…N per appointment, unique & ordered      |        |
| actor_role     | string    | yes      |                                            |        |
| notes          | string    | no       |                                            |        |
| wait_time_min  | int       | no       | minutes                                    |        |
| dwell_time_min | int       | no       | minutes                                    |        |

**Important**: Event history is **append-only**. Never overwrite prior events.

---

## 11. Exception

| Field            | Type      | Required | Notes                                      | Unique |
|------------------|-----------|----------|--------------------------------------------|--------|
| exception_id     | string    | yes      | `EXC-NNNNNN`                               | PK     |
| entity_type      | string    | yes      | Appointment / CheckInEvent / …             |        |
| entity_id        | string    | yes      |                                            |        |
| issue_type       | enum      | yes      | CAPACITY_EXCEEDED, INCOMPATIBLE_LOAD, CHECKIN_BEFORE_WINDOW, LABOR_UNAVAILABLE, NO_SHOW_UNRECORDED, OVERLAPPING_SLOT | |
| severity         | enum      | yes      | LOW, MEDIUM, HIGH, CRITICAL                |        |
| detected_at      | timestamp | yes      |                                            |        |
| description      | string    | yes      |                                            |        |
| cause_code       | string    | yes      | same as issue_type for injected cases      |        |
| resolved         | boolean   | yes      | default false                              |        |
| resolution_notes | string    | no       |                                            |        |

---

## 12. GroundTruth

| Field             | Type    | Required | Notes                          | Unique |
|-------------------|---------|----------|--------------------------------|--------|
| gt_id             | string  | yes      | `GT-NNNNNN`                    | PK     |
| entity_type       | string  | yes      |                                |        |
| entity_id         | string  | yes      |                                |        |
| issue_type        | string  | yes      |                                |        |
| expected_label    | string  | yes      |                                |        |
| expected_decision | string  | yes      | e.g. REJECT_OR_RESCHEDULE      |        |
| rule_reference    | string  | yes      | BR-…                           |        |
| severity          | string  | yes      |                                |        |
| injected          | boolean | yes      | always true for synthetic      |        |

**Rule**: Ground truth is stored in a **separate** file and must never be mixed into feature tables used for training / scoring.
