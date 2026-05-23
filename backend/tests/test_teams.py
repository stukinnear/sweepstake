"""Tests for team endpoints."""

import pytest
from httpx import AsyncClient


TOURNAMENT_PAYLOAD = {
    "name": "Test Tournament",
}

TEAM_1_PAYLOAD = {
    "name": "Alpha Team",
    "iso_code": "DE",
    "image_url": "https://example.com/de.png",
    "football_data_org_id": 101,
}

TEAM_2_PAYLOAD = {
    "name": "Beta Team",
    "iso_code": "FR",
    "image_url": None,
    "football_data_org_id": None,
}

TEAM_3_PAYLOAD = {
    "name": "Gamma Team",
    "iso_code": "GB",
    "image_url": None,
    "football_data_org_id": None,
}


def compare_item(expected: dict, actual: dict, ignore_additional_fields: bool = True, exclude_keys: list = []):
    """Helper to compare dicts while ignoring additional fields like id."""
    key_lst = expected.keys() if ignore_additional_fields else set(expected.keys()).union(set(actual.keys()))
    for key in [key for key in key_lst if key not in exclude_keys]:
        assert key in actual, f"Expected key '{key}' not found in actual"
        assert key in expected, f"Additional not expected key '{key}' found in actual"
        assert actual[key] == expected[key], f"Value mismatch for key '{key}': expected {expected[key]}, got {actual[key]}"


@pytest.mark.asyncio
async def test_create_team(client_user_1: AsyncClient):
    """POST /team creates a team for a tournament admin and returns it with an id."""
    # Create tournament first
    tournament_resp = await client_user_1.post("/tournament", json=TOURNAMENT_PAYLOAD)
    assert tournament_resp.status_code == 201
    tournament_id = tournament_resp.json()["id"]

    resp = await client_user_1.post("/team", json={**TEAM_1_PAYLOAD, "tournament_id": tournament_id})
    assert resp.status_code == 201

    data = resp.json()
    compare_item(TEAM_1_PAYLOAD, data)
    assert "id" in data
    assert data["tournament_id"] == tournament_id


@pytest.mark.asyncio
async def test_get_team_by_id(client_user_1: AsyncClient):
    """GET /team/{id} returns the correct team for a participant."""
    # Create tournament and team
    tournament_resp = await client_user_1.post("/tournament", json=TOURNAMENT_PAYLOAD)
    assert tournament_resp.status_code == 201
    tournament_id = tournament_resp.json()["id"]

    create_resp = await client_user_1.post("/team", json={**TEAM_1_PAYLOAD, "tournament_id": tournament_id})
    assert create_resp.status_code == 201
    team_id = create_resp.json()["id"]

    # Fetch
    resp = await client_user_1.get(f"/team/{team_id}")
    assert resp.status_code == 200

    data = resp.json()
    compare_item(TEAM_1_PAYLOAD, data)
    assert data["id"] == team_id
    assert data["tournament_id"] == tournament_id

    # Fetch nonexistent team - 404
    resp = await client_user_1.get("/team/9999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_all_teams(client_user_1: AsyncClient):
    """GET /team?tournament_id=X returns all teams for the tournament sorted alphabetically."""
    # Create tournament
    tournament_resp = await client_user_1.post("/tournament", json=TOURNAMENT_PAYLOAD)
    assert tournament_resp.status_code == 201
    tournament_id = tournament_resp.json()["id"]

    # Create teams in non-alphabetical order
    await client_user_1.post("/team", json={**TEAM_3_PAYLOAD, "tournament_id": tournament_id})
    await client_user_1.post("/team", json={**TEAM_1_PAYLOAD, "tournament_id": tournament_id})
    await client_user_1.post("/team", json={**TEAM_2_PAYLOAD, "tournament_id": tournament_id})

    resp = await client_user_1.get("/team", params={"tournament_id": tournament_id})
    assert resp.status_code == 200

    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 3
    # Should be sorted alphabetically by name
    expected_order = [TEAM_1_PAYLOAD, TEAM_2_PAYLOAD, TEAM_3_PAYLOAD]
    for item, expected_payload in zip(data, expected_order):
        compare_item(expected_payload, item)


@pytest.mark.asyncio
async def test_update_team(client_user_1: AsyncClient):
    """PATCH /team/{id} updates a team field (admin only)."""
    # Create tournament and team
    tournament_resp = await client_user_1.post("/tournament", json=TOURNAMENT_PAYLOAD)
    assert tournament_resp.status_code == 201
    tournament_id = tournament_resp.json()["id"]

    create_resp = await client_user_1.post("/team", json={**TEAM_1_PAYLOAD, "tournament_id": tournament_id})
    assert create_resp.status_code == 201
    team_id = create_resp.json()["id"]

    patch_resp = await client_user_1.patch(f"/team/{team_id}", json={"name": "Updated Team"})
    assert patch_resp.status_code == 200

    data = patch_resp.json()
    assert data["name"] == "Updated Team"
    # Other fields should be unchanged
    assert data["iso_code"] == TEAM_1_PAYLOAD["iso_code"]
    assert data["id"] == team_id

    # Patch nonexistent team - 404
    resp = await client_user_1.patch("/team/9999", json={"name": "Ghost"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_team(client_user_1: AsyncClient):
    """DELETE /team/{id} removes the team (admin only)."""
    # Create tournament and team
    tournament_resp = await client_user_1.post("/tournament", json=TOURNAMENT_PAYLOAD)
    assert tournament_resp.status_code == 201
    tournament_id = tournament_resp.json()["id"]

    create_resp = await client_user_1.post("/team", json={**TEAM_1_PAYLOAD, "tournament_id": tournament_id})
    assert create_resp.status_code == 201
    team_id = create_resp.json()["id"]

    del_resp = await client_user_1.delete(f"/team/{team_id}")
    assert del_resp.status_code == 204

    # Confirm it's gone
    get_resp = await client_user_1.get(f"/team/{team_id}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_access_denied_for_non_participant(client_user_1: AsyncClient, client_user_2: AsyncClient):
    """All team endpoints return 403 for a user who is not a participant or admin."""
    # User 1 creates a tournament and a team
    tournament_resp = await client_user_1.post("/tournament", json=TOURNAMENT_PAYLOAD)
    assert tournament_resp.status_code == 201
    tournament_id = tournament_resp.json()["id"]

    create_resp = await client_user_1.post("/team", json={**TEAM_1_PAYLOAD, "tournament_id": tournament_id})
    assert create_resp.status_code == 201
    team_id = create_resp.json()["id"]

    # User 2 tries to access — should be forbidden
    # GET /team/{id} - forbidden
    resp = await client_user_2.get(f"/team/{team_id}")
    assert resp.status_code == 403
    assert "Forbidden" in resp.json()["message"]
    # GET /team?tournament_id=X - forbidden
    resp = await client_user_2.get("/team", params={"tournament_id": tournament_id})
    assert resp.status_code == 403
    assert "Forbidden" in resp.json()["message"]
    # POST /team - forbidden
    resp = await client_user_2.post("/team", json={**TEAM_2_PAYLOAD, "tournament_id": tournament_id})
    assert resp.status_code == 403
    assert "Forbidden" in resp.json()["message"]
    # PATCH - forbidden
    resp = await client_user_2.patch(f"/team/{team_id}", json={"name": "Hacked"})
    assert resp.status_code == 403
    assert "Forbidden" in resp.json()["message"]
    # DELETE - forbidden
    resp = await client_user_2.delete(f"/team/{team_id}")
    assert resp.status_code == 403
    assert "Forbidden" in resp.json()["message"]
    # Final check: team is unchanged and still accessible to admin
    get_resp = await client_user_1.get(f"/team/{team_id}")
    assert get_resp.status_code == 200
    compare_item(TEAM_1_PAYLOAD, get_resp.json())


@pytest.mark.asyncio
async def test_forbidden_for_non_admin(client_user_1: AsyncClient, client_user_2: AsyncClient):
    """PATCH, DELETE, and POST /team return 403 for a participant who is not an admin."""
    # User 1 creates a tournament and a team
    tournament_resp = await client_user_1.post("/tournament", json=TOURNAMENT_PAYLOAD)
    assert tournament_resp.status_code == 201
    tournament_id = tournament_resp.json()["id"]
    join_code = tournament_resp.json()["join_code"]

    create_resp = await client_user_1.post("/team", json={**TEAM_1_PAYLOAD, "tournament_id": tournament_id})
    assert create_resp.status_code == 201
    team_id = create_resp.json()["id"]

    # User 2 joins as participant (not admin)
    join_resp = await client_user_2.post(f"/tournament/join/{join_code}")
    assert join_resp.status_code == 200

    # POST /team - forbidden (not admin)
    resp = await client_user_2.post("/team", json={**TEAM_2_PAYLOAD, "tournament_id": tournament_id})
    assert resp.status_code == 403
    assert "Forbidden" in resp.json()["message"]
    # PATCH - forbidden
    resp = await client_user_2.patch(f"/team/{team_id}", json={"name": "Hacked"})
    assert resp.status_code == 403
    assert "Forbidden" in resp.json()["message"]
    # DELETE - forbidden
    resp = await client_user_2.delete(f"/team/{team_id}")
    assert resp.status_code == 403
    assert "Forbidden" in resp.json()["message"]
    # GET /team/{id} - allowed (is participant)
    resp = await client_user_2.get(f"/team/{team_id}")
    assert resp.status_code == 200
    compare_item(TEAM_1_PAYLOAD, resp.json())
    # GET /team?tournament_id=X - allowed (is participant)
    resp = await client_user_2.get("/team", params={"tournament_id": tournament_id})
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    # Final check: team is unchanged
    get_resp = await client_user_1.get(f"/team/{team_id}")
    assert get_resp.status_code == 200
    compare_item(TEAM_1_PAYLOAD, get_resp.json())
