"""Tests for tournament endpoints."""

import json

import pytest
from httpx import AsyncClient


TOURNAMENT_1_PAYLOAD = {
    "name": "Tournament 1",
}

TOURNAMENT_2_PAYLOAD = {
    "name": "Tournament 2",
}

TOURNAMENT_3_PAYLOAD = {
    "name": "Tournament 3",
}

MATCH_1_PAYLOAD = {
    "start_datetime": "2024-01-01T12:00:00Z",
}

MATCH_2_PAYLOAD = {
    "start_datetime": "2024-01-02T12:00:00Z",
}

MATCH_3_PAYLOAD = {
    "start_datetime": "2024-01-03T12:00:00Z",
}


def compare_item(expected: dict, actual: dict, ignore_additional_fields: bool = True, exclude_keys: list = []):
    """Helper to compare dicts while ignoring additional fields like id or join_code."""
    key_lst = expected.keys() if ignore_additional_fields else set(expected.keys()).union(set(actual.keys()))
    for key in [key for key in key_lst if key not in exclude_keys]:
        assert key in actual, f"Expected key '{key}' not found in actual"
        assert key in expected, f"Additional not expected key '{key}' found in actual"
        assert actual[key] == expected[key], f"Value mismatch for key '{key}': expected {expected[key]}, got {actual[key]}"


@pytest.mark.asyncio
async def test_create_tournament(client_user_1: AsyncClient):
    """POST /tournament creates a tournament and returns it with an id and join_code."""
    resp = await client_user_1.post("/tournament", json=TOURNAMENT_1_PAYLOAD)
    assert resp.status_code == 201

    data = resp.json()
    compare_item(TOURNAMENT_1_PAYLOAD, data)
    assert "id" in data
    assert "join_code" in data
    # Creator should be both admin and participant
    assert any(u["id"] == 1 for u in data["admin_lst"])
    assert any(u["id"] == 1 for u in data["participant_lst"])


@pytest.mark.asyncio
async def test_get_tournament_by_id(client_user_1: AsyncClient):
    """GET /tournament/{id} returns the correct tournament for a participant."""
    # Create first
    create_resp = await client_user_1.post("/tournament", json=TOURNAMENT_1_PAYLOAD)
    tournament_id = create_resp.json()["id"]

    # Fetch
    resp = await client_user_1.get(f"/tournament/{tournament_id}")
    assert resp.status_code == 200

    data = resp.json()
    compare_item(TOURNAMENT_1_PAYLOAD, data)
    assert data["id"] == tournament_id

    # Fetch nonexistent tournament - 404 not found error
    resp = await client_user_1.get(f"/tournament/9999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_all_tournaments(client_user_1: AsyncClient):
    """GET /tournament and /tournament/stream returns a list of tournaments the user is a participant in."""
    # Create three tournaments
    resp = await client_user_1.post("/tournament", json=TOURNAMENT_1_PAYLOAD)
    await client_user_1.post("/match", json={**MATCH_1_PAYLOAD, "tournament_id": resp.json()["id"]})
    await client_user_1.post("/match", json={**MATCH_3_PAYLOAD, "tournament_id": resp.json()["id"]})
    resp = await client_user_1.post("/tournament", json=TOURNAMENT_2_PAYLOAD)
    await client_user_1.post("/match", json={**MATCH_1_PAYLOAD, "tournament_id": resp.json()["id"]})
    await client_user_1.post("/match", json={**MATCH_2_PAYLOAD, "tournament_id": resp.json()["id"]})
    resp = await client_user_1.post("/tournament", json=TOURNAMENT_3_PAYLOAD)
    await client_user_1.post("/match", json={**MATCH_2_PAYLOAD, "tournament_id": resp.json()["id"]})
    await client_user_1.post("/match", json={**MATCH_3_PAYLOAD, "tournament_id": resp.json()["id"]})

    # Fetch all
    resp = await client_user_1.get("/tournament")
    assert resp.status_code == 200

    expected_payloads = [TOURNAMENT_2_PAYLOAD, TOURNAMENT_1_PAYLOAD, TOURNAMENT_3_PAYLOAD]

    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 3
    # Check order of returned tournaments (should be sorted by end_date and start_date ascending)
    for item, expected_payload in zip(data, expected_payloads):
        compare_item(expected_payload, item)

    # Fetch all stremed (NDJSON)
    resp = await client_user_1.get("/tournament/stream")
    assert resp.status_code == 200
    lines = resp.text.strip().split("\n")
    assert len(lines) == 3
    for line, expected_payload in zip(lines, expected_payloads):
        data = json.loads(line)
        compare_item(expected_payload, data)



@pytest.mark.asyncio
async def test_delete_tournament(client_user_1: AsyncClient):
    """DELETE /tournament/{id} removes the tournament (admin only)."""
    # Create
    create_resp = await client_user_1.post("/tournament", json=TOURNAMENT_1_PAYLOAD)
    tournament_id = create_resp.json()["id"]

    # Delete
    del_resp = await client_user_1.delete(f"/tournament/{tournament_id}")
    assert del_resp.status_code == 204

    # Confirm it's gone
    get_resp = await client_user_1.get(f"/tournament/{tournament_id}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_access_denied_for_non_participant(client_user_1: AsyncClient, client_user_2: AsyncClient):
    """GET /tournament/{id} returns 403 for a user who is not a participant or admin."""
    # User 1 creates a tournament
    create_resp = await client_user_1.post("/tournament", json=TOURNAMENT_1_PAYLOAD)
    assert create_resp.status_code == 201
    tournament_id = create_resp.json()["id"]

    # User 2 tries to access it — should be forbidden
    # Get - forbidden
    resp = await client_user_2.get(f"/tournament/{tournament_id}")
    assert resp.status_code == 403
    assert "Forbidden" in resp.json()["message"]
    # Get All - allowed by empty list
    resp = await client_user_2.get(f"/tournament")
    assert resp.status_code == 200
    assert resp.json() == []
    # Get All Stream - allowed but empty (NDJSON streaming response)
    resp = await client_user_2.get(f"/tournament/stream")
    assert resp.status_code == 200
    assert resp.text.strip() == ""
    # Delete - forbidden
    resp = await client_user_2.delete(f"/tournament/{tournament_id}")
    assert resp.status_code == 403
    assert "Forbidden" in resp.json()["message"]
    # Patch - forbidden
    resp = await client_user_2.patch(f"/tournament/{tournament_id}", json={"name": "New Name"})
    assert resp.status_code == 403
    assert "Forbidden" in resp.json()["message"]
    # Final check if actually unchanged and still accessible to creator
    resp = await client_user_1.get(f"/tournament/{tournament_id}")
    assert resp.status_code == 200
    data = resp.json()
    compare_item(TOURNAMENT_1_PAYLOAD, data)
    assert data["id"] == tournament_id


@pytest.mark.asyncio
async def test_forbidden_for_non_admin(client_user_1: AsyncClient, client_user_2: AsyncClient):
    """PATCH and DELETE /tournament/{id} return 403 for a user who is not an admin."""
    # User 1 creates a tournament
    create_resp = await client_user_1.post("/tournament", json=TOURNAMENT_1_PAYLOAD)
    assert create_resp.status_code == 201
    tournament_id = create_resp.json()["id"]

    # User 2 tries to modify it — should be forbidden
    # Delete - forbidden
    resp = await client_user_2.delete(f"/tournament/{tournament_id}")
    assert resp.status_code == 403
    assert "Forbidden" in resp.json()["message"]
    # Patch - forbidden
    resp = await client_user_2.patch(f"/tournament/{tournament_id}", json={"name": "New Name"})
    assert resp.status_code == 403
    assert "Forbidden" in resp.json()["message"]
    # Final check if actually unchanged and still accessible to creator
    resp = await client_user_1.get(f"/tournament/{tournament_id}")
    assert resp.status_code == 200
    data = resp.json()
    compare_item(TOURNAMENT_1_PAYLOAD, data)
    assert data["id"] == tournament_id


@pytest.mark.asyncio
async def test_join_and_leave_tournament(client_user_1: AsyncClient, client_user_2: AsyncClient):
    """POST /tournament/join/{join_code} allows a user to join as participant, DELETE /tournament/leave/{id} allows leaving."""
    from tests.conftest import USER_2_PAYLOAD

    # User 1 creates a tournament
    create_resp = await client_user_1.post("/tournament", json=TOURNAMENT_1_PAYLOAD)
    assert create_resp.status_code == 201
    tournament_id = create_resp.json()["id"]
    join_code = create_resp.json()["join_code"]

    # User 2 joins the tournament
    join_resp = await client_user_2.post(f"/tournament/join/{join_code}")
    assert join_resp.status_code == 200
    data = join_resp.json()
    compare_item(TOURNAMENT_1_PAYLOAD, data)
    assert data["id"] == tournament_id
    assert any(u["id"] == USER_2_PAYLOAD["id"] for u in data["participant_lst"])

    # User 2 leaves the tournament
    leave_resp = await client_user_2.delete(f"/tournament/leave/{tournament_id}")
    assert leave_resp.status_code == 204

    # Confirm user 2 is no longer a participant but tournament still exists
    get_resp = await client_user_1.get(f"/tournament/{tournament_id}")
    assert get_resp.status_code == 200
    data = get_resp.json()
    compare_item(TOURNAMENT_1_PAYLOAD, data)
    assert data["id"] == tournament_id
    assert all(u["id"] != USER_2_PAYLOAD["id"] for u in data["participant_lst"])


@pytest.mark.asyncio
async def test_join_tournament_already_member(client_user_1: AsyncClient, client_user_2: AsyncClient):
    """POST /tournament/join/{join_code} returns 409 if the user is already a member."""
    create_resp = await client_user_1.post("/tournament", json=TOURNAMENT_1_PAYLOAD)
    assert create_resp.status_code == 201
    join_code = create_resp.json()["join_code"]

    # First join succeeds
    join_resp = await client_user_2.post(f"/tournament/join/{join_code}")
    assert join_resp.status_code == 200

    # Second join returns 409
    join_again_resp = await client_user_2.post(f"/tournament/join/{join_code}")
    assert join_again_resp.status_code == 409