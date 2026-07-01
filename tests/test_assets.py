"""Endpoint tests for assets. Shows plain asserts, async tests, and
parametrize (≈ [Theory]/[InlineData])."""
import pytest


async def test_create_pump(client):
    resp = await client.post("/assets/pumps", json={"name": "Pump A", "flow_rate_lps": 120})
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Pump A"
    assert body["asset_type"] == "pump"
    assert body["status"] == "active"


async def test_get_missing_asset_returns_404(client):
    resp = await client.get("/assets/999")
    assert resp.status_code == 404


async def test_create_pump_rejects_negative_flow(client):
    # flow_rate_lps has gt=0 validation -> 422 Unprocessable Entity
    resp = await client.post("/assets/pumps", json={"name": "Bad", "flow_rate_lps": -5})
    assert resp.status_code == 422


@pytest.mark.parametrize(
    "path,payload,expected_type",
    [
        ("/assets/pumps", {"name": "P1", "flow_rate_lps": 50}, "pump"),
        ("/assets/pipes", {"name": "Main 1", "length_m": 300, "material": "ductile iron"}, "pipe"),
        ("/assets/valves", {"name": "V1", "valve_kind": "gate"}, "valve"),
    ],
)
async def test_create_each_asset_type(client, path, payload, expected_type):
    resp = await client.post(path, json=payload)
    assert resp.status_code == 201
    assert resp.json()["asset_type"] == expected_type


async def test_list_and_filter(client):
    await client.post("/assets/pumps", json={"name": "P1"})
    await client.post("/assets/pipes", json={"name": "Pipe1"})

    all_assets = (await client.get("/assets")).json()
    assert len(all_assets) == 2

    only_pumps = (await client.get("/assets", params={"asset_type": "pump"})).json()
    assert len(only_pumps) == 1
    assert only_pumps[0]["asset_type"] == "pump"


async def test_health_uses_polymorphic_risk_score(client):
    # High-flow pump (>100 lps) gets the 1.5x load factor in its override.
    pump_id = (await client.post(
        "/assets/pumps", json={"name": "Big Pump", "flow_rate_lps": 200}
    )).json()["id"]

    # condition 4 -> base risk 40, pump override -> 40 * 1.5 = 60
    await client.post(f"/assets/{pump_id}/inspections", json={"condition_score": 4})

    health = (await client.get(f"/assets/{pump_id}/health")).json()
    assert health["latest_condition"] == 4
    assert health["risk_score"] == 60.0
    assert health["inspections_count"] == 1


async def test_health_no_inspections_defaults_to_excellent(client):
    valve_id = (await client.post("/assets/valves", json={"name": "V"})).json()["id"]
    health = (await client.get(f"/assets/{valve_id}/health")).json()
    # No inspections -> latest_condition defaults to 1, valve uses base score.
    assert health["latest_condition"] == 1
    assert health["risk_score"] == 10.0


async def test_patch_status_updates_and_returns_asset(client):
    asset_id = (await client.post("/assets/pumps", json={"name": "P"})).json()["id"]
    resp = await client.patch(f"/assets/{asset_id}/status", json={"status": "maintenance"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "maintenance"


async def test_patch_status_not_found(client):
    resp = await client.patch("/assets/9999/status", json={"status": "maintenance"})
    assert resp.status_code == 404


async def test_patch_status_missing_body_returns_422(client):
    asset_id = (await client.post("/assets/pumps", json={"name": "P"})).json()["id"]
    resp = await client.patch(f"/assets/{asset_id}/status", json={})
    assert resp.status_code == 422


async def test_patch_status_invalid_value_returns_422(client):
    asset_id = (await client.post("/assets/pumps", json={"name": "P"})).json()["id"]
    resp = await client.patch(f"/assets/{asset_id}/status", json={"status": "broken"})
    assert resp.status_code == 422

async def test_at_risk_returns_assets_sorted_by_risk(client):
    # High-flow pump (risk=60) should rank above uninspected valve (risk=10)
    await client.post("/assets/pumps", json={"name": "Big", "flow_rate_lps": 200})
    pump_id = (await client.get("/assets", params={"asset_type": "pump"})).json()[0]["id"]
    await client.post(f"/assets/{pump_id}/inspections", json={"condition_score": 4})
    await client.post("/assets/valves", json={"name": "V"})

    resp = await client.get("/assets/at-risk")
    assert resp.status_code == 200
    data = resp.json()
    assert data[0]["risk_score"] >= data[-1]["risk_score"]
    assert "risk_score" in data[0]

async def test_at_risk_empty(client):
    resp = await client.get("/assets/at-risk")
    assert resp.status_code == 200
    assert resp.json() == []
