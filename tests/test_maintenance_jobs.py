"""Endpoint tests for MaintenanceJob lifecycle."""
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _make_pump(client):
    return (await client.post("/assets/pumps", json={"name": "P", "flow_rate_lps": 200})).json()["id"]


async def _make_job(client, asset_id, **kwargs):
    payload = {"assigned_to": "Alice", "scheduled_date": "2026-07-01", **kwargs}
    return (await client.post(f"/assets/{asset_id}/maintenance-jobs", json=payload)).json()


# ---------------------------------------------------------------------------
# Tracer bullet: create a job
# ---------------------------------------------------------------------------

async def test_create_maintenance_job(client):
    asset_id = await _make_pump(client)
    resp = await client.post(
        f"/assets/{asset_id}/maintenance-jobs",
        json={"assigned_to": "Alice", "scheduled_date": "2026-07-01"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "scheduled"
    assert body["assigned_to"] == "Alice"
    assert body["asset_id"] == asset_id
    assert body["outcome"] is None
    assert body["completed_at"] is None
    assert body["post_job_condition"] is None


async def test_create_job_for_missing_asset_404(client):
    resp = await client.post(
        "/assets/999/maintenance-jobs",
        json={"assigned_to": "Alice", "scheduled_date": "2026-07-01"},
    )
    assert resp.status_code == 404


async def test_list_maintenance_jobs(client):
    asset_id = await _make_pump(client)
    await _make_job(client, asset_id)
    await _make_job(client, asset_id, assigned_to="Bob")

    resp = await client.get(f"/assets/{asset_id}/maintenance-jobs")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


async def test_list_jobs_missing_asset_404(client):
    resp = await client.get("/assets/999/maintenance-jobs")
    assert resp.status_code == 404


async def test_get_single_job(client):
    asset_id = await _make_pump(client)
    job = await _make_job(client, asset_id)
    job_id = job["id"]

    resp = await client.get(f"/maintenance-jobs/{job_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == job_id


async def test_get_missing_job_404(client):
    resp = await client.get("/maintenance-jobs/9999")
    assert resp.status_code == 404


async def test_transition_to_in_progress(client):
    asset_id = await _make_pump(client)
    job_id = (await _make_job(client, asset_id))["id"]

    resp = await client.patch(
        f"/maintenance-jobs/{job_id}/status", json={"status": "in_progress"}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "in_progress"
    assert resp.json()["completed_at"] is None


async def test_transition_to_completed_with_outcome_and_condition(client):
    asset_id = await _make_pump(client)
    job_id = (await _make_job(client, asset_id))["id"]

    resp = await client.patch(
        f"/maintenance-jobs/{job_id}/status",
        json={"status": "completed", "outcome": "resolved", "post_job_condition": 2},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "completed"
    assert body["outcome"] == "resolved"
    assert body["post_job_condition"] == 2
    assert body["completed_at"] is not None


async def test_cannot_transition_out_of_completed(client):
    asset_id = await _make_pump(client)
    job_id = (await _make_job(client, asset_id))["id"]
    await client.patch(
        f"/maintenance-jobs/{job_id}/status",
        json={"status": "completed", "outcome": "resolved"},
    )

    resp = await client.patch(
        f"/maintenance-jobs/{job_id}/status", json={"status": "in_progress"}
    )
    assert resp.status_code == 422


async def test_cannot_transition_out_of_cancelled(client):
    asset_id = await _make_pump(client)
    job_id = (await _make_job(client, asset_id))["id"]
    await client.patch(f"/maintenance-jobs/{job_id}/status", json={"status": "cancelled"})

    resp = await client.patch(
        f"/maintenance-jobs/{job_id}/status", json={"status": "scheduled"}
    )
    assert resp.status_code == 422


async def test_outcome_only_allowed_on_completed_transition(client):
    asset_id = await _make_pump(client)
    job_id = (await _make_job(client, asset_id))["id"]

    resp = await client.patch(
        f"/maintenance-jobs/{job_id}/status",
        json={"status": "in_progress", "outcome": "resolved"},
    )
    assert resp.status_code == 422


async def test_post_job_condition_only_allowed_on_completed_transition(client):
    asset_id = await _make_pump(client)
    job_id = (await _make_job(client, asset_id))["id"]

    resp = await client.patch(
        f"/maintenance-jobs/{job_id}/status",
        json={"status": "in_progress", "post_job_condition": 1},
    )
    assert resp.status_code == 422


async def test_completing_without_outcome_returns_422(client):
    asset_id = await _make_pump(client)
    job_id = (await _make_job(client, asset_id))["id"]

    resp = await client.patch(
        f"/maintenance-jobs/{job_id}/status", json={"status": "completed"}
    )
    assert resp.status_code == 422


async def test_cancelled_job_sets_completed_at(client):
    asset_id = await _make_pump(client)
    job_id = (await _make_job(client, asset_id))["id"]

    resp = await client.patch(
        f"/maintenance-jobs/{job_id}/status", json={"status": "cancelled"}
    )
    assert resp.status_code == 200
    assert resp.json()["completed_at"] is not None


async def test_completed_job_post_condition_drives_risk_score(client):
    # Pump with high flow; inspection sets condition=4 → risk=60
    asset_id = await _make_pump(client)
    await client.post(f"/assets/{asset_id}/inspections", json={"condition_score": 4})

    job_id = (await _make_job(client, asset_id))["id"]
    await client.patch(
        f"/maintenance-jobs/{job_id}/status",
        json={"status": "completed", "outcome": "resolved", "post_job_condition": 1},
    )

    # post_job_condition=1 should override inspection score 4.
    # Pump load factor: flow_rate_lps=200 > 100 → ×1.5; 1×10×1.5 = 15.0
    health = (await client.get(f"/assets/{asset_id}/health")).json()
    assert health["risk_score"] == 15.0


async def test_newer_inspection_overrides_stale_job_condition(client):
    # Job completes with post_job_condition=1 (good), then a new bad inspection arrives.
    asset_id = await _make_pump(client)
    job_id = (await _make_job(client, asset_id))["id"]
    await client.patch(
        f"/maintenance-jobs/{job_id}/status",
        json={"status": "completed", "outcome": "resolved", "post_job_condition": 1},
    )
    # New inspection recorded after the job — condition 5 is critical.
    await client.post(f"/assets/{asset_id}/inspections", json={"condition_score": 5})

    # The newer inspection should win: 5 × 10 × 1.5 (pump load) = 75.0
    health = (await client.get(f"/assets/{asset_id}/health")).json()
    assert health["risk_score"] == 75.0


