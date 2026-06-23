# post_job_condition on MaintenanceJob drives risk_score(), not a synthetic Inspection

When a MaintenanceJob is completed, the technician can record a `post_job_condition` score (1–5) directly on the job. When present, this overrides the Inspection-based `latest_condition()` in `risk_score()` for that asset.

We considered three alternatives:

- **Synthetic Inspection**: auto-insert an Inspection record on job completion. Rejected — it pollutes the inspection history with records that were never the result of a real inspection visit.
- **post_job_condition on MaintenanceJob** _(chosen)_: the technician's observed condition is recorded on the job itself. It feeds into risk scoring without touching the inspection log.
- **Flat multiplier**: halve the risk score whenever the most recent job is `completed`. Rejected — it's arbitrary and not grounded in any observed condition.

The consequence is that `risk_score()` has two possible condition sources: `Inspection.condition_score` (the default) and `MaintenanceJob.post_job_condition` (when a completed job exists with one set). Code reading `risk_score()` must be aware of this.
