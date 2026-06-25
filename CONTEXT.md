# Water Asset System

A service for tracking water-utility infrastructure assets (pumps, pipes, valves), their inspection history, and the maintenance work performed on them.

## Language

### Assets

**Asset**: A water infrastructure component — pump, pipe, or valve — tracked for physical condition and operational status.
_Avoid_: equipment, device, unit

**AssetStatus**: The operational state of an asset at a point in time.
Values: `active` | `inactive` | `maintenance`
_Avoid_: state, mode

**zone**: A geographic or operational grouping that an asset belongs to.
_Avoid_: area, region, sector

### Inspections

**Inspection**: A recorded observation of an asset's physical condition at a point in time, scored 1–5 (1 = excellent, 5 = critical).
_Avoid_: survey, assessment, check

**condition_score**: The 1–5 integer recorded on an Inspection representing observed physical condition.
_Avoid_: rating, grade, health score

**latest_condition**: The condition_score from the most recent Inspection for an asset, or 1 if no inspections exist. Used as input to risk_score().
_Avoid_: current condition, last score

**risk_score**: A computed urgency signal for an asset. Higher = more urgent maintenance needed. Varies by asset subtype.
_Avoid_: priority, severity, health

### Maintenance Jobs

**MaintenanceJob**: A first-class record of maintenance work on an asset, covering its full lifecycle from scheduling through completion.
_Avoid_: work order, task, ticket

**JobStatus**: The lifecycle state of a MaintenanceJob.
Values: `scheduled` → `in_progress` → `completed` | `cancelled`. Terminal states: `completed`, `cancelled`.
_Avoid_: status, state

**assigned_to**: The free-text name of the person or team responsible for executing a MaintenanceJob.
_Avoid_: technician, assignee, owner

**Outcome**: The machine-readable result of a completed MaintenanceJob.
Values: `resolved` | `partially_resolved` | `deferred`. Only set when JobStatus is `completed`.
_Avoid_: result, resolution, conclusion

**scheduled_date**: The date a MaintenanceJob is planned to occur.
_Avoid_: planned date, due date

**completed_at**: The timestamp when a MaintenanceJob reached `completed` or `cancelled`.
_Avoid_: finished at, end time

**InvalidTransition**: A domain exception raised when a requested JobStatus change violates the lifecycle rules — e.g. exiting a terminal state, or completing without an outcome. Translates to HTTP 422 at the application boundary.
_Avoid_: ValidationError, StateError

**post_job_condition**: An optional 1–5 condition score recorded by the technician on job completion. When present, overrides Inspection-based condition in risk_score() for the asset.
_Avoid_: post-maintenance score, outcome score
