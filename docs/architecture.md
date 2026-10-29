# Architecture & Design Decisions

## Domain Model

```
Facility 1──* Dock 1──* YardSlot
    │
    ├──* LaborShift
    │
    └──* Appointment *──1 Shipment 1──* HandlingRequirement
              │
              ├──1 Carrier 1──* Vehicle
              │
              └──* CheckInEvent   (append-only history)
              └──* Exception      (labelled anomalies)
```

GroundTruth is a parallel, non-feature table that labels the injected anomalies.

## Generation Pipeline

1. **Master data** (deterministic IDs from counters + seed)
2. **Labor shifts** for every facility × day
3. **Baseline appointments** that respect capacity & compatibility
4. **Event simulation** (state machine + realistic timings)
5. **Edge-case injection** with explicit ground-truth labels
6. **Export** CSV + JSON + schema.sql + manifest
7. **Validation** + **reproducibility** checks

## Key Design Choices

- **Append-only events** – every status change is a new CheckInEvent row. The `appointments.status` column is a denormalised current-state convenience only.
- **Derived metrics** – service duration, wait time and utilisation are calculated from source attributes / events, never randomly assigned.
- **Fixed seed** – `random.Random(seed)` is the single source of randomness; regenerating with the same seed yields identical files (verified by SHA-256).
- **Separate ground truth** – anomalies are present in operational tables so that detectors can be scored, but the correct labels live only in `ground_truth.csv`.
- **Configurable volume** – `--mode starter` for quick local iteration, `--mode full` for the challenge target (10 fac / 100 docks / 20 k appts / ~100 k events).

## Exception Paths Implemented

| Issue type              | How it is injected                                      | Expected decision          |
|-------------------------|---------------------------------------------------------|----------------------------|
| CAPACITY_EXCEEDED       | Confirm appointment on an already-full dock             | REJECT_OR_RESCHEDULE       |
| INCOMPATIBLE_LOAD       | Re-assign appointment to an incompatible dock           | REJECT_INCOMPATIBLE        |
| CHECKIN_BEFORE_WINDOW   | Emit CHECK_IN event on the day before the appointment   | FLAG_EARLY_CHECKIN         |
| LABOR_UNAVAILABLE       | Confirm appointment with no covering labor shift        | BLOCK_OR_ESCALATE          |
| NO_SHOW_UNRECORDED      | Leave status = CONFIRMED with no NO_SHOW event          | RECORD_NO_SHOW             |

## Measurable Outputs

- Dock utilisation = booked appointments / (daily_capacity × horizon_days)
- Average wait time (minutes between CHECK_IN and LOADING/UNLOADING start)
- Exception rate by issue_type and severity
- Lifecycle completion rate (DEPARTED / total confirmed)
