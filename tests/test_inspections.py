"""Endpoint tests for inspections + the asset<->inspection relationship."""


async def test_add_inspection_to_missing_asset_404(client):
    resp = await client.post("/assets/123/inspections", json={"condition_score": 3})
    assert resp.status_code == 404


async def test_add_and_list_inspections(client):
    asset_id = (await client.post("/assets/pipes", json={"name": "Main"})).json()["id"]

    await client.post(f"/assets/{asset_id}/inspections", json={"condition_score": 2, "notes": "ok"})
    await client.post(f"/assets/{asset_id}/inspections", json={"condition_score": 5, "notes": "leak"})

    items = (await client.get(f"/assets/{asset_id}/inspections")).json()
    assert len(items) == 2
    # Relationship is ordered newest-first; both scores are present.
    scores = {i["condition_score"] for i in items}
    assert scores == {2, 5}


async def test_inspection_score_validation(client):
    asset_id = (await client.post("/assets/valves", json={"name": "V"})).json()["id"]
    # condition_score must be 1..5
    resp = await client.post(f"/assets/{asset_id}/inspections", json={"condition_score": 9})
    assert resp.status_code == 422
