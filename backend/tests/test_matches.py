"""Tests for match endpoints."""

import pytest
from httpx import AsyncClient


TOURNAMENT_PAYLOAD = {
    "name": "Test Tournament",
}

TEAM_HOME_PAYLOAD = {
    "name": "Home Team",
    "iso_code": "DE",
    "image_url": None,
    "football_data_org_id": None,
}

TEAM_AWAY_PAYLOAD = {
    "name": "Away Team",
    "iso_code": "FR",
    "image_url": None,
    "football_data_org_id": None,
}

MATCH_1_PAYLOAD = {
    "start_datetime": "2026-06-01T15:00:00",
    "home_goals": None,
    "away_goals": None,
    "football_data_org_id": None,
}

MATCH_2_PAYLOAD = {
    "start_datetime": "2026-06-02T18:00:00",
    "home_goals": None,
    "away_goals": None,
    "football_data_org_id": None,
}

MATCH_3_PAYLOAD = {
    "start_datetime": "2026-06-03T21:00:00",
    "home_goals": None,
    "away_goals": None,
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
async def test_create_match(client_user_1: AsyncClient):
    """POST /match creates a match for a tournament admin and returns it with an id and nested teams."""
    # Create tournament and two teams
    tournament_resp = await client_user_1.post("/tournament", json=TOURNAMENT_PAYLOAD)
    assert tournament_resp.status_code == 201
    tournament_id = tournament_resp.json()["id"]

    home_resp = await client_user_1.post("/team", json={**TEAM_HOME_PAYLOAD, "tournament_id": tournament_id})
    assert home_resp.status_code == 201
    home_team_id = home_resp.json()["id"]

    away_resp = await client_user_1.post("/team", json={**TEAM_AWAY_PAYLOAD, "tournament_id": tournament_id})
    assert away_resp.status_code == 201
    away_team_id = away_resp.json()["id"]

    resp = await client_user_1.post("/match", json={
        **MATCH_1_PAYLOAD,
        "tournament_id": tournament_id,
        "home_team_id": home_team_id,
        "away_team_id": away_team_id,
    })
    assert resp.status_code == 201

    data = resp.json()
    compare_item(MATCH_1_PAYLOAD, data)
    assert "id" in data
    assert data["tournament_id"] == tournament_id
    assert data["home_team_id"] == home_team_id
    assert data["away_team_id"] == away_team_id
    # Nested team objects should be returned
    assert data["home_team"]["id"] == home_team_id
    assert data["away_team"]["id"] == away_team_id
    compare_item(TEAM_HOME_PAYLOAD, data["home_team"])
    compare_item(TEAM_AWAY_PAYLOAD, data["away_team"])


@pytest.mark.asyncio
async def test_create_match_without_teams(client_user_1: AsyncClient):
    """POST /match creates a match with no teams assigned (teams optional)."""
    tournament_resp = await client_user_1.post("/tournament", json=TOURNAMENT_PAYLOAD)
    assert tournament_resp.status_code == 201
    tournament_id = tournament_resp.json()["id"]

    resp = await client_user_1.post("/match", json={
        **MATCH_1_PAYLOAD,
        "tournament_id": tournament_id,
    })
    assert resp.status_code == 201

    data = resp.json()
    compare_item(MATCH_1_PAYLOAD, data)
    assert data["home_team_id"] is None
    assert data["away_team_id"] is None
    assert data["home_team"] is None
    assert data["away_team"] is None


@pytest.mark.asyncio
async def test_get_match_by_id(client_user_1: AsyncClient):
    """GET /match/{id} returns the correct match for a participant."""
    # Create tournament and match
    tournament_resp = await client_user_1.post("/tournament", json=TOURNAMENT_PAYLOAD)
    assert tournament_resp.status_code == 201
    tournament_id = tournament_resp.json()["id"]

    create_resp = await client_user_1.post("/match", json={**MATCH_1_PAYLOAD, "tournament_id": tournament_id})
    assert create_resp.status_code == 201
    match_id = create_resp.json()["id"]

    # Fetch
    resp = await client_user_1.get(f"/match/{match_id}")
    assert resp.status_code == 200

    data = resp.json()
    compare_item(MATCH_1_PAYLOAD, data)
    assert data["id"] == match_id
    assert data["tournament_id"] == tournament_id

    # Fetch nonexistent match - 404
    resp = await client_user_1.get("/match/9999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_all_matches(client_user_1: AsyncClient):
    """GET /match?tournament_id=X returns all matches sorted by start_datetime ascending."""
    # Create tournament
    tournament_resp = await client_user_1.post("/tournament", json=TOURNAMENT_PAYLOAD)
    assert tournament_resp.status_code == 201
    tournament_id = tournament_resp.json()["id"]

    # Create matches in reverse chronological order
    await client_user_1.post("/match", json={**MATCH_3_PAYLOAD, "tournament_id": tournament_id})
    await client_user_1.post("/match", json={**MATCH_1_PAYLOAD, "tournament_id": tournament_id})
    await client_user_1.post("/match", json={**MATCH_2_PAYLOAD, "tournament_id": tournament_id})

    resp = await client_user_1.get("/match", params={"tournament_id": tournament_id})
    assert resp.status_code == 200

    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 3
    # Should be sorted by start_datetime ascending
    expected_order = [MATCH_1_PAYLOAD, MATCH_2_PAYLOAD, MATCH_3_PAYLOAD]
    for item, expected_payload in zip(data, expected_order):
        compare_item(expected_payload, item)


@pytest.mark.asyncio
async def test_update_match(client_user_1: AsyncClient):
    """PATCH /match/{id} updates a match field (admin only)."""
    # Create tournament, teams, and match
    tournament_resp = await client_user_1.post("/tournament", json=TOURNAMENT_PAYLOAD)
    assert tournament_resp.status_code == 201
    tournament_id = tournament_resp.json()["id"]

    home_resp = await client_user_1.post("/team", json={**TEAM_HOME_PAYLOAD, "tournament_id": tournament_id})
    assert home_resp.status_code == 201
    home_team_id = home_resp.json()["id"]

    create_resp = await client_user_1.post("/match", json={**MATCH_1_PAYLOAD, "tournament_id": tournament_id})
    assert create_resp.status_code == 201
    match_id = create_resp.json()["id"]

    # Update goals and assign home team
    patch_resp = await client_user_1.patch(f"/match/{match_id}", json={
        "home_goals": 2,
        "away_goals": 1,
        "home_team_id": home_team_id,
    })
    assert patch_resp.status_code == 200

    data = patch_resp.json()
    assert data["home_goals"] == 2
    assert data["away_goals"] == 1
    assert data["home_team_id"] == home_team_id
    assert data["home_team"]["id"] == home_team_id
    # Other fields should be unchanged
    assert data["id"] == match_id
    assert data["tournament_id"] == tournament_id

    # Patch nonexistent match - 404
    resp = await client_user_1.patch("/match/9999", json={"home_goals": 0})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_match(client_user_1: AsyncClient):
    """DELETE /match/{id} removes the match (admin only)."""
    # Create tournament and match
    tournament_resp = await client_user_1.post("/tournament", json=TOURNAMENT_PAYLOAD)
    assert tournament_resp.status_code == 201
    tournament_id = tournament_resp.json()["id"]

    create_resp = await client_user_1.post("/match", json={**MATCH_1_PAYLOAD, "tournament_id": tournament_id})
    assert create_resp.status_code == 201
    match_id = create_resp.json()["id"]

    del_resp = await client_user_1.delete(f"/match/{match_id}")
    assert del_resp.status_code == 204

    # Confirm it's gone
    get_resp = await client_user_1.get(f"/match/{match_id}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_access_denied_for_non_participant(client_user_1: AsyncClient, client_user_2: AsyncClient):
    """All match endpoints return 403 for a user who is not a participant or admin."""
    # User 1 creates a tournament and a match
    tournament_resp = await client_user_1.post("/tournament", json=TOURNAMENT_PAYLOAD)
    assert tournament_resp.status_code == 201
    tournament_id = tournament_resp.json()["id"]

    create_resp = await client_user_1.post("/match", json={**MATCH_1_PAYLOAD, "tournament_id": tournament_id})
    assert create_resp.status_code == 201
    match_id = create_resp.json()["id"]

    # User 2 tries to access — should be forbidden
    # GET /match/{id} - forbidden
    resp = await client_user_2.get(f"/match/{match_id}")
    assert resp.status_code == 403
    assert "Forbidden" in resp.json()["message"]
    # GET /match?tournament_id=X - forbidden
    resp = await client_user_2.get("/match", params={"tournament_id": tournament_id})
    assert resp.status_code == 403
    assert "Forbidden" in resp.json()["message"]
    # POST /match - forbidden
    resp = await client_user_2.post("/match", json={**MATCH_2_PAYLOAD, "tournament_id": tournament_id})
    assert resp.status_code == 403
    assert "Forbidden" in resp.json()["message"]
    # PATCH - forbidden
    resp = await client_user_2.patch(f"/match/{match_id}", json={"home_goals": 9})
    assert resp.status_code == 403
    assert "Forbidden" in resp.json()["message"]
    # DELETE - forbidden
    resp = await client_user_2.delete(f"/match/{match_id}")
    assert resp.status_code == 403
    assert "Forbidden" in resp.json()["message"]
    # Final check: match is unchanged and still accessible to admin
    get_resp = await client_user_1.get(f"/match/{match_id}")
    assert get_resp.status_code == 200
    compare_item(MATCH_1_PAYLOAD, get_resp.json())


@pytest.mark.asyncio
async def test_forbidden_for_non_admin(client_user_1: AsyncClient, client_user_2: AsyncClient):
    """PATCH, DELETE, and POST /match return 403 for a participant who is not an admin."""
    # User 1 creates a tournament and a match
    tournament_resp = await client_user_1.post("/tournament", json=TOURNAMENT_PAYLOAD)
    assert tournament_resp.status_code == 201
    tournament_id = tournament_resp.json()["id"]
    join_code = tournament_resp.json()["join_code"]

    create_resp = await client_user_1.post("/match", json={**MATCH_1_PAYLOAD, "tournament_id": tournament_id})
    assert create_resp.status_code == 201
    match_id = create_resp.json()["id"]

    # User 2 joins as participant (not admin)
    join_resp = await client_user_2.post(f"/tournament/join/{join_code}")
    assert join_resp.status_code == 200

    # POST /match - forbidden (not admin)
    resp = await client_user_2.post("/match", json={**MATCH_2_PAYLOAD, "tournament_id": tournament_id})
    assert resp.status_code == 403
    assert "Forbidden" in resp.json()["message"]
    # PATCH - forbidden
    resp = await client_user_2.patch(f"/match/{match_id}", json={"home_goals": 9})
    assert resp.status_code == 403
    assert "Forbidden" in resp.json()["message"]
    # DELETE - forbidden
    resp = await client_user_2.delete(f"/match/{match_id}")
    assert resp.status_code == 403
    assert "Forbidden" in resp.json()["message"]
    # GET /match/{id} - allowed (is participant)
    resp = await client_user_2.get(f"/match/{match_id}")
    assert resp.status_code == 200
    compare_item(MATCH_1_PAYLOAD, resp.json())
    # GET /match?tournament_id=X - allowed (is participant)
    resp = await client_user_2.get("/match", params={"tournament_id": tournament_id})
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    # Final check: match is unchanged
    get_resp = await client_user_1.get(f"/match/{match_id}")
    assert get_resp.status_code == 200
    compare_item(MATCH_1_PAYLOAD, get_resp.json())
