"""Tests for group and stage endpoints."""

import pytest
from httpx import AsyncClient


TOURNAMENT_PAYLOAD = {
    "name": "Test Tournament",
}

TEAM_PAYLOAD = {
    "name": "Alpha Team",
    "iso_code": "DE",
    "image_url": "https://example.com/de.png",
    "football_data_org_id": 101,
}

GROUP_1_PAYLOAD = {
    "name": "Group A",
    "winner_team_id": None,
    "winner_points": 8,
}

GROUP_2_PAYLOAD = {
    "name": "Group B",
    "winner_team_id": None,
    "winner_points": 0,
}

GROUP_3_PAYLOAD = {
    "name": "Group C",
    "winner_team_id": None,
    "winner_points": 10,
}

STAGE_1_PAYLOAD = {
    "name": "Quarter-finals",
    "winner_team_id": None,
    "winner_points": None,
}

STAGE_2_PAYLOAD = {
    "name": "Semi-finals",
    "winner_team_id": None,
    "winner_points": 5,
}

STAGE_3_PAYLOAD = {
    "name": "Final",
    "winner_team_id": None,
    "winner_points": 20,
}


def compare_item(expected: dict, actual: dict, ignore_additional_fields: bool = True, exclude_keys: list = []):
    """Helper to compare dicts while ignoring additional fields like id."""
    key_lst = expected.keys() if ignore_additional_fields else set(expected.keys()).union(set(actual.keys()))
    for key in [key for key in key_lst if key not in exclude_keys]:
        assert key in actual, f"Expected key '{key}' not found in actual"
        assert key in expected, f"Additional not expected key '{key}' found in actual"
        assert actual[key] == expected[key], f"Value mismatch for key '{key}': expected {expected[key]}, got {actual[key]}"


# ===========================================================================
# Group tests
# ===========================================================================

@pytest.mark.asyncio
async def test_create_group(client_user_1: AsyncClient):
    """POST /group creates a group for a tournament admin and returns it with an id."""
    tournament_resp = await client_user_1.post("/tournament", json=TOURNAMENT_PAYLOAD)
    assert tournament_resp.status_code == 201
    tournament_id = tournament_resp.json()["id"]

    resp = await client_user_1.post("/group", json={**GROUP_1_PAYLOAD, "tournament_id": tournament_id})
    assert resp.status_code == 201

    data = resp.json()
    compare_item(GROUP_1_PAYLOAD, data)
    assert "id" in data
    assert data["tournament_id"] == tournament_id
    assert data["winner"] is None


@pytest.mark.asyncio
async def test_create_group_with_winner(client_user_1: AsyncClient):
    """POST /group with a winner_team_id returns nested winner object."""
    tournament_resp = await client_user_1.post("/tournament", json=TOURNAMENT_PAYLOAD)
    assert tournament_resp.status_code == 201
    tournament_id = tournament_resp.json()["id"]

    team_resp = await client_user_1.post("/team", json={**TEAM_PAYLOAD, "tournament_id": tournament_id})
    assert team_resp.status_code == 201
    team_id = team_resp.json()["id"]

    resp = await client_user_1.post("/group", json={**GROUP_1_PAYLOAD, "tournament_id": tournament_id, "winner_team_id": team_id})
    assert resp.status_code == 201

    data = resp.json()
    assert data["winner_team_id"] == team_id
    assert data["winner"] is not None
    assert data["winner"]["id"] == team_id
    assert data["winner"]["name"] == TEAM_PAYLOAD["name"]


@pytest.mark.asyncio
async def test_get_group_by_id(client_user_1: AsyncClient):
    """GET /group/{id} returns the correct group for a participant."""
    tournament_resp = await client_user_1.post("/tournament", json=TOURNAMENT_PAYLOAD)
    assert tournament_resp.status_code == 201
    tournament_id = tournament_resp.json()["id"]

    create_resp = await client_user_1.post("/group", json={**GROUP_1_PAYLOAD, "tournament_id": tournament_id})
    assert create_resp.status_code == 201
    group_id = create_resp.json()["id"]

    resp = await client_user_1.get(f"/group/{group_id}")
    assert resp.status_code == 200

    data = resp.json()
    compare_item(GROUP_1_PAYLOAD, data)
    assert data["id"] == group_id
    assert data["tournament_id"] == tournament_id

    # Nonexistent group - 404
    resp = await client_user_1.get("/group/9999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_all_groups(client_user_1: AsyncClient):
    """GET /group?tournament_id=X returns all groups for the tournament sorted alphabetically."""
    tournament_resp = await client_user_1.post("/tournament", json=TOURNAMENT_PAYLOAD)
    assert tournament_resp.status_code == 201
    tournament_id = tournament_resp.json()["id"]

    # Create in non-alphabetical order
    await client_user_1.post("/group", json={**GROUP_3_PAYLOAD, "tournament_id": tournament_id})
    await client_user_1.post("/group", json={**GROUP_1_PAYLOAD, "tournament_id": tournament_id})
    await client_user_1.post("/group", json={**GROUP_2_PAYLOAD, "tournament_id": tournament_id})

    resp = await client_user_1.get("/group", params={"tournament_id": tournament_id})
    assert resp.status_code == 200

    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 3
    # Should be sorted alphabetically by name
    expected_order = [GROUP_1_PAYLOAD, GROUP_2_PAYLOAD, GROUP_3_PAYLOAD]
    for item, expected_payload in zip(data, expected_order):
        compare_item(expected_payload, item)


@pytest.mark.asyncio
async def test_update_group(client_user_1: AsyncClient):
    """PATCH /group/{id} updates a group field (admin only)."""
    tournament_resp = await client_user_1.post("/tournament", json=TOURNAMENT_PAYLOAD)
    assert tournament_resp.status_code == 201
    tournament_id = tournament_resp.json()["id"]

    create_resp = await client_user_1.post("/group", json={**GROUP_1_PAYLOAD, "tournament_id": tournament_id})
    assert create_resp.status_code == 201
    group_id = create_resp.json()["id"]

    patch_resp = await client_user_1.patch(f"/group/{group_id}", json={"name": "Group X"})
    assert patch_resp.status_code == 200

    data = patch_resp.json()
    assert data["name"] == "Group X"
    # Other fields should be unchanged
    assert data["winner_points"] == GROUP_1_PAYLOAD["winner_points"]
    assert data["id"] == group_id

    # Patch nonexistent group - 404
    resp = await client_user_1.patch("/group/9999", json={"name": "Ghost"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_group_winner(client_user_1: AsyncClient):
    """PATCH /group/{id} can set a winner team and returns nested winner object."""
    tournament_resp = await client_user_1.post("/tournament", json=TOURNAMENT_PAYLOAD)
    assert tournament_resp.status_code == 201
    tournament_id = tournament_resp.json()["id"]

    team_resp = await client_user_1.post("/team", json={**TEAM_PAYLOAD, "tournament_id": tournament_id})
    assert team_resp.status_code == 201
    team_id = team_resp.json()["id"]

    create_resp = await client_user_1.post("/group", json={**GROUP_1_PAYLOAD, "tournament_id": tournament_id})
    assert create_resp.status_code == 201
    group_id = create_resp.json()["id"]

    patch_resp = await client_user_1.patch(f"/group/{group_id}", json={"winner_team_id": team_id})
    assert patch_resp.status_code == 200

    data = patch_resp.json()
    assert data["winner_team_id"] == team_id
    assert data["winner"] is not None
    assert data["winner"]["id"] == team_id


@pytest.mark.asyncio
async def test_delete_group(client_user_1: AsyncClient):
    """DELETE /group/{id} removes the group (admin only)."""
    tournament_resp = await client_user_1.post("/tournament", json=TOURNAMENT_PAYLOAD)
    assert tournament_resp.status_code == 201
    tournament_id = tournament_resp.json()["id"]

    create_resp = await client_user_1.post("/group", json={**GROUP_1_PAYLOAD, "tournament_id": tournament_id})
    assert create_resp.status_code == 201
    group_id = create_resp.json()["id"]

    del_resp = await client_user_1.delete(f"/group/{group_id}")
    assert del_resp.status_code == 204

    # Confirm it's gone
    get_resp = await client_user_1.get(f"/group/{group_id}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_group_access_denied_for_non_participant(client_user_1: AsyncClient, client_user_2: AsyncClient):
    """All group endpoints return 403 for a user who is not a participant or admin."""
    tournament_resp = await client_user_1.post("/tournament", json=TOURNAMENT_PAYLOAD)
    assert tournament_resp.status_code == 201
    tournament_id = tournament_resp.json()["id"]

    create_resp = await client_user_1.post("/group", json={**GROUP_1_PAYLOAD, "tournament_id": tournament_id})
    assert create_resp.status_code == 201
    group_id = create_resp.json()["id"]

    # User 2 tries to access — should be forbidden
    resp = await client_user_2.get(f"/group/{group_id}")
    assert resp.status_code == 403
    assert "Forbidden" in resp.json()["message"]

    resp = await client_user_2.get("/group", params={"tournament_id": tournament_id})
    assert resp.status_code == 403
    assert "Forbidden" in resp.json()["message"]

    resp = await client_user_2.post("/group", json={**GROUP_2_PAYLOAD, "tournament_id": tournament_id})
    assert resp.status_code == 403
    assert "Forbidden" in resp.json()["message"]

    resp = await client_user_2.patch(f"/group/{group_id}", json={"name": "Hacked"})
    assert resp.status_code == 403
    assert "Forbidden" in resp.json()["message"]

    resp = await client_user_2.delete(f"/group/{group_id}")
    assert resp.status_code == 403
    assert "Forbidden" in resp.json()["message"]

    # Final check: group is unchanged and still accessible to admin
    get_resp = await client_user_1.get(f"/group/{group_id}")
    assert get_resp.status_code == 200
    compare_item(GROUP_1_PAYLOAD, get_resp.json())


@pytest.mark.asyncio
async def test_group_forbidden_for_non_admin(client_user_1: AsyncClient, client_user_2: AsyncClient):
    """PATCH, DELETE, and POST /group return 403 for a participant who is not an admin."""
    tournament_resp = await client_user_1.post("/tournament", json=TOURNAMENT_PAYLOAD)
    assert tournament_resp.status_code == 201
    tournament_id = tournament_resp.json()["id"]
    join_code = tournament_resp.json()["join_code"]

    create_resp = await client_user_1.post("/group", json={**GROUP_1_PAYLOAD, "tournament_id": tournament_id})
    assert create_resp.status_code == 201
    group_id = create_resp.json()["id"]

    # User 2 joins as participant (not admin)
    join_resp = await client_user_2.post(f"/tournament/join/{join_code}")
    assert join_resp.status_code == 200

    resp = await client_user_2.post("/group", json={**GROUP_2_PAYLOAD, "tournament_id": tournament_id})
    assert resp.status_code == 403
    assert "Forbidden" in resp.json()["message"]

    resp = await client_user_2.patch(f"/group/{group_id}", json={"name": "Hacked"})
    assert resp.status_code == 403
    assert "Forbidden" in resp.json()["message"]

    resp = await client_user_2.delete(f"/group/{group_id}")
    assert resp.status_code == 403
    assert "Forbidden" in resp.json()["message"]

    # GET endpoints are allowed for participants
    resp = await client_user_2.get(f"/group/{group_id}")
    assert resp.status_code == 200
    compare_item(GROUP_1_PAYLOAD, resp.json())

    resp = await client_user_2.get("/group", params={"tournament_id": tournament_id})
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    # Final check: group is unchanged
    get_resp = await client_user_1.get(f"/group/{group_id}")
    assert get_resp.status_code == 200
    compare_item(GROUP_1_PAYLOAD, get_resp.json())


# ===========================================================================
# Stage tests
# ===========================================================================

@pytest.mark.asyncio
async def test_create_stage(client_user_1: AsyncClient):
    """POST /stage creates a stage for a tournament admin and returns it with an id."""
    tournament_resp = await client_user_1.post("/tournament", json=TOURNAMENT_PAYLOAD)
    assert tournament_resp.status_code == 201
    tournament_id = tournament_resp.json()["id"]

    resp = await client_user_1.post("/stage", json={**STAGE_1_PAYLOAD, "tournament_id": tournament_id})
    assert resp.status_code == 201

    data = resp.json()
    compare_item(STAGE_1_PAYLOAD, data)
    assert "id" in data
    assert data["tournament_id"] == tournament_id
    assert data["winner"] is None


@pytest.mark.asyncio
async def test_create_stage_with_winner(client_user_1: AsyncClient):
    """POST /stage with a winner_team_id returns nested winner object."""
    tournament_resp = await client_user_1.post("/tournament", json=TOURNAMENT_PAYLOAD)
    assert tournament_resp.status_code == 201
    tournament_id = tournament_resp.json()["id"]

    team_resp = await client_user_1.post("/team", json={**TEAM_PAYLOAD, "tournament_id": tournament_id})
    assert team_resp.status_code == 201
    team_id = team_resp.json()["id"]

    resp = await client_user_1.post("/stage", json={**STAGE_1_PAYLOAD, "tournament_id": tournament_id, "winner_team_id": team_id})
    assert resp.status_code == 201

    data = resp.json()
    assert data["winner_team_id"] == team_id
    assert data["winner"] is not None
    assert data["winner"]["id"] == team_id
    assert data["winner"]["name"] == TEAM_PAYLOAD["name"]


@pytest.mark.asyncio
async def test_get_stage_by_id(client_user_1: AsyncClient):
    """GET /stage/{id} returns the correct stage for a participant."""
    tournament_resp = await client_user_1.post("/tournament", json=TOURNAMENT_PAYLOAD)
    assert tournament_resp.status_code == 201
    tournament_id = tournament_resp.json()["id"]

    create_resp = await client_user_1.post("/stage", json={**STAGE_1_PAYLOAD, "tournament_id": tournament_id})
    assert create_resp.status_code == 201
    stage_id = create_resp.json()["id"]

    resp = await client_user_1.get(f"/stage/{stage_id}")
    assert resp.status_code == 200

    data = resp.json()
    compare_item(STAGE_1_PAYLOAD, data)
    assert data["id"] == stage_id
    assert data["tournament_id"] == tournament_id

    # Nonexistent stage - 404
    resp = await client_user_1.get("/stage/9999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_all_stages(client_user_1: AsyncClient):
    """GET /stage?tournament_id=X returns all stages for the tournament sorted alphabetically."""
    tournament_resp = await client_user_1.post("/tournament", json=TOURNAMENT_PAYLOAD)
    assert tournament_resp.status_code == 201
    tournament_id = tournament_resp.json()["id"]

    # Create in non-alphabetical order
    await client_user_1.post("/stage", json={**STAGE_3_PAYLOAD, "tournament_id": tournament_id})
    await client_user_1.post("/stage", json={**STAGE_1_PAYLOAD, "tournament_id": tournament_id})
    await client_user_1.post("/stage", json={**STAGE_2_PAYLOAD, "tournament_id": tournament_id})

    resp = await client_user_1.get("/stage", params={"tournament_id": tournament_id})
    assert resp.status_code == 200

    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 3
    # Should be sorted alphabetically by name
    expected_order = [STAGE_3_PAYLOAD, STAGE_1_PAYLOAD, STAGE_2_PAYLOAD]  # Final, Quarter-finals, Semi-finals
    for item, expected_payload in zip(data, expected_order):
        compare_item(expected_payload, item)


@pytest.mark.asyncio
async def test_update_stage(client_user_1: AsyncClient):
    """PATCH /stage/{id} updates a stage field (admin only)."""
    tournament_resp = await client_user_1.post("/tournament", json=TOURNAMENT_PAYLOAD)
    assert tournament_resp.status_code == 201
    tournament_id = tournament_resp.json()["id"]

    create_resp = await client_user_1.post("/stage", json={**STAGE_2_PAYLOAD, "tournament_id": tournament_id})
    assert create_resp.status_code == 201
    stage_id = create_resp.json()["id"]

    patch_resp = await client_user_1.patch(f"/stage/{stage_id}", json={"name": "Grand Final"})
    assert patch_resp.status_code == 200

    data = patch_resp.json()
    assert data["name"] == "Grand Final"
    # Other fields should be unchanged
    assert data["winner_points"] == STAGE_2_PAYLOAD["winner_points"]
    assert data["id"] == stage_id

    # Patch nonexistent stage - 404
    resp = await client_user_1.patch("/stage/9999", json={"name": "Ghost"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_stage_winner(client_user_1: AsyncClient):
    """PATCH /stage/{id} can set a winner team and returns nested winner object."""
    tournament_resp = await client_user_1.post("/tournament", json=TOURNAMENT_PAYLOAD)
    assert tournament_resp.status_code == 201
    tournament_id = tournament_resp.json()["id"]

    team_resp = await client_user_1.post("/team", json={**TEAM_PAYLOAD, "tournament_id": tournament_id})
    assert team_resp.status_code == 201
    team_id = team_resp.json()["id"]

    create_resp = await client_user_1.post("/stage", json={**STAGE_1_PAYLOAD, "tournament_id": tournament_id})
    assert create_resp.status_code == 201
    stage_id = create_resp.json()["id"]

    patch_resp = await client_user_1.patch(f"/stage/{stage_id}", json={"winner_team_id": team_id})
    assert patch_resp.status_code == 200

    data = patch_resp.json()
    assert data["winner_team_id"] == team_id
    assert data["winner"] is not None
    assert data["winner"]["id"] == team_id


@pytest.mark.asyncio
async def test_delete_stage(client_user_1: AsyncClient):
    """DELETE /stage/{id} removes the stage (admin only)."""
    tournament_resp = await client_user_1.post("/tournament", json=TOURNAMENT_PAYLOAD)
    assert tournament_resp.status_code == 201
    tournament_id = tournament_resp.json()["id"]

    create_resp = await client_user_1.post("/stage", json={**STAGE_1_PAYLOAD, "tournament_id": tournament_id})
    assert create_resp.status_code == 201
    stage_id = create_resp.json()["id"]

    del_resp = await client_user_1.delete(f"/stage/{stage_id}")
    assert del_resp.status_code == 204

    # Confirm it's gone
    get_resp = await client_user_1.get(f"/stage/{stage_id}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_stage_access_denied_for_non_participant(client_user_1: AsyncClient, client_user_2: AsyncClient):
    """All stage endpoints return 403 for a user who is not a participant or admin."""
    tournament_resp = await client_user_1.post("/tournament", json=TOURNAMENT_PAYLOAD)
    assert tournament_resp.status_code == 201
    tournament_id = tournament_resp.json()["id"]

    create_resp = await client_user_1.post("/stage", json={**STAGE_1_PAYLOAD, "tournament_id": tournament_id})
    assert create_resp.status_code == 201
    stage_id = create_resp.json()["id"]

    # User 2 tries to access — should be forbidden
    resp = await client_user_2.get(f"/stage/{stage_id}")
    assert resp.status_code == 403
    assert "Forbidden" in resp.json()["message"]

    resp = await client_user_2.get("/stage", params={"tournament_id": tournament_id})
    assert resp.status_code == 403
    assert "Forbidden" in resp.json()["message"]

    resp = await client_user_2.post("/stage", json={**STAGE_2_PAYLOAD, "tournament_id": tournament_id})
    assert resp.status_code == 403
    assert "Forbidden" in resp.json()["message"]

    resp = await client_user_2.patch(f"/stage/{stage_id}", json={"name": "Hacked"})
    assert resp.status_code == 403
    assert "Forbidden" in resp.json()["message"]

    resp = await client_user_2.delete(f"/stage/{stage_id}")
    assert resp.status_code == 403
    assert "Forbidden" in resp.json()["message"]

    # Final check: stage is unchanged and still accessible to admin
    get_resp = await client_user_1.get(f"/stage/{stage_id}")
    assert get_resp.status_code == 200
    compare_item(STAGE_1_PAYLOAD, get_resp.json())


@pytest.mark.asyncio
async def test_stage_forbidden_for_non_admin(client_user_1: AsyncClient, client_user_2: AsyncClient):
    """PATCH, DELETE, and POST /stage return 403 for a participant who is not an admin."""
    tournament_resp = await client_user_1.post("/tournament", json=TOURNAMENT_PAYLOAD)
    assert tournament_resp.status_code == 201
    tournament_id = tournament_resp.json()["id"]
    join_code = tournament_resp.json()["join_code"]

    create_resp = await client_user_1.post("/stage", json={**STAGE_1_PAYLOAD, "tournament_id": tournament_id})
    assert create_resp.status_code == 201
    stage_id = create_resp.json()["id"]

    # User 2 joins as participant (not admin)
    join_resp = await client_user_2.post(f"/tournament/join/{join_code}")
    assert join_resp.status_code == 200

    resp = await client_user_2.post("/stage", json={**STAGE_2_PAYLOAD, "tournament_id": tournament_id})
    assert resp.status_code == 403
    assert "Forbidden" in resp.json()["message"]

    resp = await client_user_2.patch(f"/stage/{stage_id}", json={"name": "Hacked"})
    assert resp.status_code == 403
    assert "Forbidden" in resp.json()["message"]

    resp = await client_user_2.delete(f"/stage/{stage_id}")
    assert resp.status_code == 403
    assert "Forbidden" in resp.json()["message"]

    # GET endpoints are allowed for participants
    resp = await client_user_2.get(f"/stage/{stage_id}")
    assert resp.status_code == 200
    compare_item(STAGE_1_PAYLOAD, resp.json())

    resp = await client_user_2.get("/stage", params={"tournament_id": tournament_id})
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    # Final check: stage is unchanged
    get_resp = await client_user_1.get(f"/stage/{stage_id}")
    assert get_resp.status_code == 200
    compare_item(STAGE_1_PAYLOAD, get_resp.json())
