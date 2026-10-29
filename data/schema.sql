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
