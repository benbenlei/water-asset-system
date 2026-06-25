"""Pure-Python unit tests for MaintenanceJob.transition_to().

No DB, no HTTP, no async — the state machine is tested directly on the model.
"""
from datetime import date

import pytest

from app.models import InvalidTransition, JobStatus, MaintenanceJob, Outcome


def _job(**kwargs) -> MaintenanceJob:
    defaults = dict(
        asset_id=1,
        assigned_to="Alice",
        scheduled_date=date.today(),
        status=JobStatus.SCHEDULED,
    )
    return MaintenanceJob(**{**defaults, **kwargs})


def test_scheduled_to_in_progress():
    job = _job()
    job.transition_to(JobStatus.IN_PROGRESS)
    assert job.status == JobStatus.IN_PROGRESS
    assert job.completed_at is None


def test_in_progress_to_completed_sets_fields():
    job = _job(status=JobStatus.IN_PROGRESS)
    job.transition_to(JobStatus.COMPLETED, outcome=Outcome.RESOLVED, post_job_condition=2)
    assert job.status == JobStatus.COMPLETED
    assert job.outcome == Outcome.RESOLVED
    assert job.post_job_condition == 2
    assert job.completed_at is not None


def test_cancelled_sets_completed_at():
    job = _job(status=JobStatus.IN_PROGRESS)
    job.transition_to(JobStatus.CANCELLED)
    assert job.status == JobStatus.CANCELLED
    assert job.completed_at is not None


def test_completed_requires_outcome():
    job = _job(status=JobStatus.IN_PROGRESS)
    with pytest.raises(InvalidTransition, match="outcome is required"):
        job.transition_to(JobStatus.COMPLETED)


def test_outcome_forbidden_outside_completed():
    job = _job()
    with pytest.raises(InvalidTransition, match="outcome can only be set"):
        job.transition_to(JobStatus.IN_PROGRESS, outcome=Outcome.RESOLVED)


def test_post_job_condition_forbidden_outside_completed():
    job = _job()
    with pytest.raises(InvalidTransition, match="post_job_condition can only be set"):
        job.transition_to(JobStatus.IN_PROGRESS, post_job_condition=3)


def test_cannot_exit_completed():
    job = _job(status=JobStatus.COMPLETED)
    with pytest.raises(InvalidTransition, match="terminal"):
        job.transition_to(JobStatus.IN_PROGRESS)


def test_cannot_exit_cancelled():
    job = _job(status=JobStatus.CANCELLED)
    with pytest.raises(InvalidTransition, match="terminal"):
        job.transition_to(JobStatus.SCHEDULED)
