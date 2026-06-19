"""Tests for prediction endpoints: PredictTournament, PredictGroup, PredictStage, PredictMatch."""

import pytest
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# Shared setup payloads
# ---------------------------------------------------------------------------

TOURNAMENT_PAYLOAD = {"name": "Predict Test Tournament"}

TEAM_PAYLOAD = {"name": "Team Alpha", "iso_code": "DE", "image_url": None, "football_data_org_id": None}
TEAM_2_PAYLOAD = {"name": "Team Beta", "iso_code": "FR", "image_url": None, "football_data_org_id": None}

GROUP_PAYLOAD = {"name": "Group A", "winner_team_id": None, "winner_points": 8}
STAGE_PAYLOAD = {"name": "Quarter-finals", "winner_team_id": None, "winner_points": None}

MATCH_PAYLOAD = {
    "start_datetime": "2030-06-10T15:00:00",
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


# ===========================================================================
# PredictTournament
# ===========================================================================

@pytest.mark.asyncio
async def test_create_predict_tournament(client_user_1: AsyncClient):
    """POST /predict/tournament creates a prediction and returns it with nested team."""
    t = await client_user_1.post("/tournament", json=TOURNAMENT_PAYLOAD)
    assert t.status_code == 201
    tournament_id = t.json()["id"]

    team = await client_user_1.post("/team", json={**TEAM_PAYLOAD, "tournament_id": tournament_id})
    assert team.status_code == 201
    team_id = team.json()["id"]

    # Create a future match so predictions can be submitted before the tournament starts
    m = await client_user_1.post("/match", json={**MATCH_PAYLOAD, "tournament_id": tournament_id})
    assert m.status_code == 201

    resp = await client_user_1.post("/predict/tournament", json={"tournament_id": tournament_id, "winner_team_id": team_id})
    assert resp.status_code == 201
    data = resp.json()
    assert data["tournament_id"] == tournament_id
    assert data["user_id"] == 1
    assert data["winner_team_id"] == team_id
    assert data["winner_team"]["id"] == team_id


@pytest.mark.asyncio
async def test_create_predict_tournament_without_team(client_user_1: AsyncClient):
    """POST /predict/tournament with no winner_team_id is allowed."""
    t = await client_user_1.post("/tournament", json=TOURNAMENT_PAYLOAD)
    assert t.status_code == 201
    tournament_id = t.json()["id"]

    # Create a future match so predictions can be submitted before the tournament starts
    m = await client_user_1.post("/match", json={**MATCH_PAYLOAD, "tournament_id": tournament_id})
    assert m.status_code == 201

    resp = await client_user_1.post("/predict/tournament", json={"tournament_id": tournament_id})
    assert resp.status_code == 201
    data = resp.json()
    assert data["winner_team_id"] is None
    assert data["winner_team"] is None


@pytest.mark.asyncio
async def test_update_predict_tournament(client_user_1: AsyncClient):
    """POST /predict/tournament again updates (upserts) an existing prediction."""
    t = await client_user_1.post("/tournament", json=TOURNAMENT_PAYLOAD)
    assert t.status_code == 201
    tournament_id = t.json()["id"]

    team = await client_user_1.post("/team", json={**TEAM_PAYLOAD, "tournament_id": tournament_id})
    assert team.status_code == 201
    team_id = team.json()["id"]

    # Create a future match so predictions can be submitted before the tournament starts
    m = await client_user_1.post("/match", json={**MATCH_PAYLOAD, "tournament_id": tournament_id})
    assert m.status_code == 201

    # Initial prediction without team
    resp = await client_user_1.post("/predict/tournament", json={"tournament_id": tournament_id})
    assert resp.status_code == 201
    assert resp.json()["winner_team_id"] is None

    # Update to set winner team
    resp = await client_user_1.post("/predict/tournament", json={"tournament_id": tournament_id, "winner_team_id": team_id})
    assert resp.status_code == 201
    assert resp.json()["winner_team_id"] == team_id


@pytest.mark.asyncio
async def test_get_predict_tournaments(client_user_1: AsyncClient, client_user_2: AsyncClient):
    """GET /predict/tournament returns the calling user's own prediction by default."""
    t = await client_user_1.post("/tournament", json=TOURNAMENT_PAYLOAD)
    assert t.status_code == 201
    tournament_id = t.json()["id"]
    join_code = t.json()["join_code"]

    # Create a future match so predictions can be submitted before the tournament starts
    m = await client_user_1.post("/match", json={**MATCH_PAYLOAD, "tournament_id": tournament_id})
    assert m.status_code == 201

    # User 2 joins and both predict
    join_resp = await client_user_2.post(f"/tournament/join/{join_code}")
    assert join_resp.status_code == 200

    await client_user_1.post("/predict/tournament", json={"tournament_id": tournament_id})
    await client_user_2.post("/predict/tournament", json={"tournament_id": tournament_id})

    # Each user gets only their own prediction by default
    resp = await client_user_1.get(f"/predict/tournament/{tournament_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["user_id"] == 1

    # Admin (user 1) can retrieve user 2's prediction by specifying user_id
    resp = await client_user_1.get(f"/predict/tournament/{tournament_id}", params={"user_id": 2})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["user_id"] == 2


@pytest.mark.asyncio
async def test_predict_tournament_forbidden_non_participant(client_user_1: AsyncClient, client_user_2: AsyncClient):
    """Non-participants cannot create or read tournament predictions."""
    t = await client_user_1.post("/tournament", json=TOURNAMENT_PAYLOAD)
    assert t.status_code == 201
    tournament_id = t.json()["id"]

    # User 2 not a participant
    resp = await client_user_2.post("/predict/tournament", json={"tournament_id": tournament_id})
    assert resp.status_code == 403
    assert "Forbidden" in resp.json()["message"]

    resp = await client_user_2.get(f"/predict/tournament/{tournament_id}")
    assert resp.status_code == 403
    assert "Forbidden" in resp.json()["message"]


# ===========================================================================
# PredictGroup
# ===========================================================================

@pytest.mark.asyncio
async def test_create_predict_group(client_user_1: AsyncClient):
    """POST /predict/group creates a prediction and returns it with nested team."""
    t = await client_user_1.post("/tournament", json=TOURNAMENT_PAYLOAD)
    assert t.status_code == 201
    tournament_id = t.json()["id"]

    g = await client_user_1.post("/group", json={**GROUP_PAYLOAD, "tournament_id": tournament_id})
    assert g.status_code == 201
    group_id = g.json()["id"]

    # Team must belong to the group so the group start_datetime can be determined
    team = await client_user_1.post("/team", json={**TEAM_PAYLOAD, "tournament_id": tournament_id, "group_id": group_id})
    assert team.status_code == 201
    team_id = team.json()["id"]

    # Create a future match linked to the group's team so predictions can be submitted
    m = await client_user_1.post("/match", json={**MATCH_PAYLOAD, "tournament_id": tournament_id, "home_team_id": team_id})
    assert m.status_code == 201

    resp = await client_user_1.post("/predict/group", json={"group_id": group_id, "winner_team_id": team_id})
    assert resp.status_code == 201
    data = resp.json()
    assert data["group_id"] == group_id
    assert data["user_id"] == 1
    assert data["winner_team_id"] == team_id
    assert data["winner_team"]["id"] == team_id


@pytest.mark.asyncio
async def test_create_predict_group_without_team(client_user_1: AsyncClient):
    """POST /predict/group with no winner_team_id is allowed."""
    t = await client_user_1.post("/tournament", json=TOURNAMENT_PAYLOAD)
    assert t.status_code == 201
    tournament_id = t.json()["id"]

    g = await client_user_1.post("/group", json={**GROUP_PAYLOAD, "tournament_id": tournament_id})
    assert g.status_code == 201
    group_id = g.json()["id"]

    # Team must belong to the group so the group start_datetime can be determined
    team = await client_user_1.post("/team", json={**TEAM_PAYLOAD, "tournament_id": tournament_id, "group_id": group_id})
    assert team.status_code == 201
    team_id = team.json()["id"]

    # Create a future match linked to the group's team so predictions can be submitted
    m = await client_user_1.post("/match", json={**MATCH_PAYLOAD, "tournament_id": tournament_id, "home_team_id": team_id})
    assert m.status_code == 201

    resp = await client_user_1.post("/predict/group", json={"group_id": group_id})
    assert resp.status_code == 201
    data = resp.json()
    assert data["winner_team_id"] is None
    assert data["winner_team"] is None


@pytest.mark.asyncio
async def test_update_predict_group(client_user_1: AsyncClient):
    """POST /predict/group again updates (upserts) an existing prediction."""
    t = await client_user_1.post("/tournament", json=TOURNAMENT_PAYLOAD)
    assert t.status_code == 201
    tournament_id = t.json()["id"]

    g = await client_user_1.post("/group", json={**GROUP_PAYLOAD, "tournament_id": tournament_id})
    assert g.status_code == 201
    group_id = g.json()["id"]

    # Team must belong to the group so the group start_datetime can be determined
    team = await client_user_1.post("/team", json={**TEAM_PAYLOAD, "tournament_id": tournament_id, "group_id": group_id})
    assert team.status_code == 201
    team_id = team.json()["id"]

    # Create a future match linked to the group's team so predictions can be submitted
    m = await client_user_1.post("/match", json={**MATCH_PAYLOAD, "tournament_id": tournament_id, "home_team_id": team_id})
    assert m.status_code == 201

    await client_user_1.post("/predict/group", json={"group_id": group_id})
    resp = await client_user_1.post("/predict/group", json={"group_id": group_id, "winner_team_id": team_id})
    assert resp.status_code == 201
    assert resp.json()["winner_team_id"] == team_id


@pytest.mark.asyncio
async def test_get_predict_groups(client_user_1: AsyncClient, client_user_2: AsyncClient):
    """GET /predict/group returns the calling user's own prediction by default."""
    t = await client_user_1.post("/tournament", json=TOURNAMENT_PAYLOAD)
    assert t.status_code == 201
    tournament_id = t.json()["id"]
    join_code = t.json()["join_code"]

    g = await client_user_1.post("/group", json={**GROUP_PAYLOAD, "tournament_id": tournament_id})
    assert g.status_code == 201
    group_id = g.json()["id"]

    # Team must belong to the group so the group start_datetime can be determined
    team = await client_user_1.post("/team", json={**TEAM_PAYLOAD, "tournament_id": tournament_id, "group_id": group_id})
    assert team.status_code == 201
    team_id = team.json()["id"]

    # Create a future match linked to the group's team so predictions can be submitted
    m = await client_user_1.post("/match", json={**MATCH_PAYLOAD, "tournament_id": tournament_id, "home_team_id": team_id})
    assert m.status_code == 201

    join_resp = await client_user_2.post(f"/tournament/join/{join_code}")
    assert join_resp.status_code == 200

    await client_user_1.post("/predict/group", json={"group_id": group_id})
    await client_user_2.post("/predict/group", json={"group_id": group_id})

    # Each user gets only their own prediction by default
    resp = await client_user_1.get(f"/predict/group/{group_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["user_id"] == 1

    resp = await client_user_2.get(f"/predict/group/{group_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["user_id"] == 2


@pytest.mark.asyncio
async def test_get_predict_groups_by_tournament(client_user_1: AsyncClient, client_user_2: AsyncClient):
    """GET /predict/group?tournament_id= returns the calling user's own group predictions."""
    t = await client_user_1.post("/tournament", json=TOURNAMENT_PAYLOAD)
    assert t.status_code == 201
    tournament_id = t.json()["id"]
    join_code = t.json()["join_code"]

    g = await client_user_1.post("/group", json={**GROUP_PAYLOAD, "tournament_id": tournament_id})
    assert g.status_code == 201
    group_id = g.json()["id"]

    # Team must belong to the group so the group start_datetime can be determined
    team = await client_user_1.post("/team", json={**TEAM_PAYLOAD, "tournament_id": tournament_id, "group_id": group_id})
    assert team.status_code == 201
    team_id = team.json()["id"]

    # Create a future match linked to the group's team so predictions can be submitted
    m = await client_user_1.post("/match", json={**MATCH_PAYLOAD, "tournament_id": tournament_id, "home_team_id": team_id})
    assert m.status_code == 201

    join_resp = await client_user_2.post(f"/tournament/join/{join_code}")
    assert join_resp.status_code == 200

    await client_user_1.post("/predict/group", json={"group_id": group_id})
    await client_user_2.post("/predict/group", json={"group_id": group_id})

    # User 1 gets only their own predictions
    resp = await client_user_1.get("/predict/group", params={"tournament_id": tournament_id})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["user_id"] == 1

    # User 2 gets only their own predictions
    resp = await client_user_2.get("/predict/group", params={"tournament_id": tournament_id})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["user_id"] == 2


@pytest.mark.asyncio
async def test_predict_group_non_existent_group(client_user_1: AsyncClient):
    """POST /predict/group with a non-existent group returns 404."""
    resp = await client_user_1.post("/predict/group", json={"group_id": 9999})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_predict_group_forbidden_non_participant(client_user_1: AsyncClient, client_user_2: AsyncClient):
    """Non-participants cannot create or read group predictions."""
    t = await client_user_1.post("/tournament", json=TOURNAMENT_PAYLOAD)
    assert t.status_code == 201
    tournament_id = t.json()["id"]

    g = await client_user_1.post("/group", json={**GROUP_PAYLOAD, "tournament_id": tournament_id})
    assert g.status_code == 201
    group_id = g.json()["id"]

    resp = await client_user_2.post("/predict/group", json={"group_id": group_id})
    assert resp.status_code == 403
    assert "Forbidden" in resp.json()["message"]

    resp = await client_user_2.get(f"/predict/group/{group_id}")
    assert resp.status_code == 403
    assert "Forbidden" in resp.json()["message"]


# ===========================================================================
# PredictStage
# ===========================================================================

@pytest.mark.asyncio
async def test_create_predict_stage(client_user_1: AsyncClient):
    """POST /predict/stage creates a prediction and returns it with nested team."""
    t = await client_user_1.post("/tournament", json=TOURNAMENT_PAYLOAD)
    assert t.status_code == 201
    tournament_id = t.json()["id"]

    s = await client_user_1.post("/stage", json={**STAGE_PAYLOAD, "tournament_id": tournament_id})
    assert s.status_code == 201
    stage_id = s.json()["id"]

    team = await client_user_1.post("/team", json={**TEAM_PAYLOAD, "tournament_id": tournament_id})
    assert team.status_code == 201
    team_id = team.json()["id"]

    # Create a future match in the stage so predictions can be submitted
    m = await client_user_1.post("/match", json={**MATCH_PAYLOAD, "tournament_id": tournament_id, "stage_id": stage_id})
    assert m.status_code == 201

    resp = await client_user_1.post("/predict/stage", json={"stage_id": stage_id, "winner_team_id": team_id})
    assert resp.status_code == 201
    data = resp.json()
    assert data["stage_id"] == stage_id
    assert data["user_id"] == 1
    assert data["winner_team_id"] == team_id
    assert data["winner_team"]["id"] == team_id


@pytest.mark.asyncio
async def test_create_predict_stage_without_team(client_user_1: AsyncClient):
    """POST /predict/stage with no winner_team_id is allowed."""
    t = await client_user_1.post("/tournament", json=TOURNAMENT_PAYLOAD)
    assert t.status_code == 201
    tournament_id = t.json()["id"]

    s = await client_user_1.post("/stage", json={**STAGE_PAYLOAD, "tournament_id": tournament_id})
    assert s.status_code == 201
    stage_id = s.json()["id"]

    # Create a future match in the stage so predictions can be submitted
    m = await client_user_1.post("/match", json={**MATCH_PAYLOAD, "tournament_id": tournament_id, "stage_id": stage_id})
    assert m.status_code == 201

    resp = await client_user_1.post("/predict/stage", json={"stage_id": stage_id})
    assert resp.status_code == 201
    data = resp.json()
    assert data["winner_team_id"] is None
    assert data["winner_team"] is None


@pytest.mark.asyncio
async def test_update_predict_stage(client_user_1: AsyncClient):
    """POST /predict/stage again updates (upserts) an existing prediction."""
    t = await client_user_1.post("/tournament", json=TOURNAMENT_PAYLOAD)
    assert t.status_code == 201
    tournament_id = t.json()["id"]

    s = await client_user_1.post("/stage", json={**STAGE_PAYLOAD, "tournament_id": tournament_id})
    assert s.status_code == 201
    stage_id = s.json()["id"]

    team = await client_user_1.post("/team", json={**TEAM_PAYLOAD, "tournament_id": tournament_id})
    assert team.status_code == 201
    team_id = team.json()["id"]

    # Create a future match in the stage so predictions can be submitted
    m = await client_user_1.post("/match", json={**MATCH_PAYLOAD, "tournament_id": tournament_id, "stage_id": stage_id})
    assert m.status_code == 201

    await client_user_1.post("/predict/stage", json={"stage_id": stage_id})
    resp = await client_user_1.post("/predict/stage", json={"stage_id": stage_id, "winner_team_id": team_id})
    assert resp.status_code == 201
    assert resp.json()["winner_team_id"] == team_id


@pytest.mark.asyncio
async def test_get_predict_stages(client_user_1: AsyncClient, client_user_2: AsyncClient):
    """GET /predict/stage returns the calling user's own prediction by default."""
    t = await client_user_1.post("/tournament", json=TOURNAMENT_PAYLOAD)
    assert t.status_code == 201
    tournament_id = t.json()["id"]
    join_code = t.json()["join_code"]

    s = await client_user_1.post("/stage", json={**STAGE_PAYLOAD, "tournament_id": tournament_id})
    assert s.status_code == 201
    stage_id = s.json()["id"]

    # Create a future match in the stage so predictions can be submitted
    m = await client_user_1.post("/match", json={**MATCH_PAYLOAD, "tournament_id": tournament_id, "stage_id": stage_id})
    assert m.status_code == 201

    join_resp = await client_user_2.post(f"/tournament/join/{join_code}")
    assert join_resp.status_code == 200

    await client_user_1.post("/predict/stage", json={"stage_id": stage_id})
    await client_user_2.post("/predict/stage", json={"stage_id": stage_id})

    # Each user gets only their own prediction by default
    resp = await client_user_1.get(f"/predict/stage/{stage_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["user_id"] == 1

    resp = await client_user_2.get(f"/predict/stage/{stage_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["user_id"] == 2


@pytest.mark.asyncio
async def test_get_predict_stages_by_tournament(client_user_1: AsyncClient, client_user_2: AsyncClient):
    """GET /predict/stage?tournament_id= returns the calling user's own stage predictions."""
    t = await client_user_1.post("/tournament", json=TOURNAMENT_PAYLOAD)
    assert t.status_code == 201
    tournament_id = t.json()["id"]
    join_code = t.json()["join_code"]

    s = await client_user_1.post("/stage", json={**STAGE_PAYLOAD, "tournament_id": tournament_id})
    assert s.status_code == 201
    stage_id = s.json()["id"]

    # Create a future match in the stage so predictions can be submitted
    m = await client_user_1.post("/match", json={**MATCH_PAYLOAD, "tournament_id": tournament_id, "stage_id": stage_id})
    assert m.status_code == 201

    join_resp = await client_user_2.post(f"/tournament/join/{join_code}")
    assert join_resp.status_code == 200

    await client_user_1.post("/predict/stage", json={"stage_id": stage_id})
    await client_user_2.post("/predict/stage", json={"stage_id": stage_id})

    # User 1 gets only their own predictions
    resp = await client_user_1.get("/predict/stage", params={"tournament_id": tournament_id})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["user_id"] == 1

    # User 2 gets only their own predictions
    resp = await client_user_2.get("/predict/stage", params={"tournament_id": tournament_id})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["user_id"] == 2


@pytest.mark.asyncio
async def test_predict_stage_non_existent_stage(client_user_1: AsyncClient):
    """POST /predict/stage with a non-existent stage returns 404."""
    resp = await client_user_1.post("/predict/stage", json={"stage_id": 9999})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_predict_stage_forbidden_non_participant(client_user_1: AsyncClient, client_user_2: AsyncClient):
    """Non-participants cannot create or read stage predictions."""
    t = await client_user_1.post("/tournament", json=TOURNAMENT_PAYLOAD)
    assert t.status_code == 201
    tournament_id = t.json()["id"]

    s = await client_user_1.post("/stage", json={**STAGE_PAYLOAD, "tournament_id": tournament_id})
    assert s.status_code == 201
    stage_id = s.json()["id"]

    resp = await client_user_2.post("/predict/stage", json={"stage_id": stage_id})
    assert resp.status_code == 403
    assert "Forbidden" in resp.json()["message"]

    resp = await client_user_2.get(f"/predict/stage/{stage_id}")
    assert resp.status_code == 403
    assert "Forbidden" in resp.json()["message"]


# ===========================================================================
# PredictMatch
# ===========================================================================

@pytest.mark.asyncio
async def test_create_predict_match(client_user_1: AsyncClient):
    """POST /predict/match creates a prediction and returns it with scores."""
    t = await client_user_1.post("/tournament", json=TOURNAMENT_PAYLOAD)
    assert t.status_code == 201
    tournament_id = t.json()["id"]

    m = await client_user_1.post("/match", json={**MATCH_PAYLOAD, "tournament_id": tournament_id})
    assert m.status_code == 201
    match_id = m.json()["id"]

    resp = await client_user_1.post("/predict/match", json={"match_id": match_id, "home_score": 2, "away_score": 1})
    assert resp.status_code == 201
    data = resp.json()
    assert data["match_id"] == match_id
    assert data["user_id"] == 1
    assert data["home_score"] == 2
    assert data["away_score"] == 1


@pytest.mark.asyncio
async def test_create_predict_match_without_scores(client_user_1: AsyncClient):
    """POST /predict/match with no scores is allowed."""
    t = await client_user_1.post("/tournament", json=TOURNAMENT_PAYLOAD)
    assert t.status_code == 201
    tournament_id = t.json()["id"]

    m = await client_user_1.post("/match", json={**MATCH_PAYLOAD, "tournament_id": tournament_id})
    assert m.status_code == 201
    match_id = m.json()["id"]

    resp = await client_user_1.post("/predict/match", json={"match_id": match_id})
    assert resp.status_code == 201
    data = resp.json()
    assert data["home_score"] is None
    assert data["away_score"] is None


@pytest.mark.asyncio
async def test_update_predict_match(client_user_1: AsyncClient):
    """POST /predict/match again updates (upserts) an existing prediction."""
    t = await client_user_1.post("/tournament", json=TOURNAMENT_PAYLOAD)
    assert t.status_code == 201
    tournament_id = t.json()["id"]

    m = await client_user_1.post("/match", json={**MATCH_PAYLOAD, "tournament_id": tournament_id})
    assert m.status_code == 201
    match_id = m.json()["id"]

    # Initial prediction
    await client_user_1.post("/predict/match", json={"match_id": match_id, "home_score": 0, "away_score": 0})

    # Update scores
    resp = await client_user_1.post("/predict/match", json={"match_id": match_id, "home_score": 3, "away_score": 2})
    assert resp.status_code == 201
    data = resp.json()
    assert data["home_score"] == 3
    assert data["away_score"] == 2


@pytest.mark.asyncio
async def test_get_predict_matches(client_user_1: AsyncClient, client_user_2: AsyncClient):
    """GET /predict/match returns the calling user's own prediction by default."""
    t = await client_user_1.post("/tournament", json=TOURNAMENT_PAYLOAD)
    assert t.status_code == 201
    tournament_id = t.json()["id"]
    join_code = t.json()["join_code"]

    m = await client_user_1.post("/match", json={**MATCH_PAYLOAD, "tournament_id": tournament_id})
    assert m.status_code == 201
    match_id = m.json()["id"]

    join_resp = await client_user_2.post(f"/tournament/join/{join_code}")
    assert join_resp.status_code == 200

    await client_user_1.post("/predict/match", json={"match_id": match_id, "home_score": 1, "away_score": 0})
    await client_user_2.post("/predict/match", json={"match_id": match_id, "home_score": 2, "away_score": 2})

    # Each user gets only their own prediction by default
    resp = await client_user_1.get(f"/predict/match/{match_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["user_id"] == 1
    assert data[0]["home_score"] == 1
    assert data[0]["away_score"] == 0

    resp = await client_user_2.get(f"/predict/match/{match_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["user_id"] == 2
    assert data[0]["home_score"] == 2
    assert data[0]["away_score"] == 2


@pytest.mark.asyncio
async def test_get_predict_matches_by_tournament(client_user_1: AsyncClient, client_user_2: AsyncClient):
    """GET /predict/match?tournament_id= returns the calling user's own match predictions."""
    t = await client_user_1.post("/tournament", json=TOURNAMENT_PAYLOAD)
    assert t.status_code == 201
    tournament_id = t.json()["id"]
    join_code = t.json()["join_code"]

    m = await client_user_1.post("/match", json={**MATCH_PAYLOAD, "tournament_id": tournament_id})
    assert m.status_code == 201
    match_id = m.json()["id"]

    join_resp = await client_user_2.post(f"/tournament/join/{join_code}")
    assert join_resp.status_code == 200

    await client_user_1.post("/predict/match", json={"match_id": match_id, "home_score": 1, "away_score": 0})
    await client_user_2.post("/predict/match", json={"match_id": match_id, "home_score": 2, "away_score": 2})

    # User 1 gets only their own predictions
    resp = await client_user_1.get("/predict/match", params={"tournament_id": tournament_id})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["user_id"] == 1

    # User 2 gets only their own predictions
    resp = await client_user_2.get("/predict/match", params={"tournament_id": tournament_id})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["user_id"] == 2


@pytest.mark.asyncio
async def test_predict_match_non_existent_match(client_user_1: AsyncClient):
    """POST /predict/match with a non-existent match returns 404."""
    resp = await client_user_1.post("/predict/match", json={"match_id": 9999, "home_score": 1, "away_score": 0})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_predict_match_forbidden_non_participant(client_user_1: AsyncClient, client_user_2: AsyncClient):
    """Non-participants cannot create or read match predictions."""
    t = await client_user_1.post("/tournament", json=TOURNAMENT_PAYLOAD)
    assert t.status_code == 201
    tournament_id = t.json()["id"]

    m = await client_user_1.post("/match", json={**MATCH_PAYLOAD, "tournament_id": tournament_id})
    assert m.status_code == 201
    match_id = m.json()["id"]

    resp = await client_user_2.post("/predict/match", json={"match_id": match_id, "home_score": 1, "away_score": 0})
    assert resp.status_code == 403
    assert "Forbidden" in resp.json()["message"]

    resp = await client_user_2.get(f"/predict/match/{match_id}")
    assert resp.status_code == 403
    assert "Forbidden" in resp.json()["message"]


@pytest.mark.asyncio
async def test_predict_match_participant_can_predict(client_user_1: AsyncClient, client_user_2: AsyncClient):
    """Participants (non-admin) can create and read match predictions."""
    t = await client_user_1.post("/tournament", json=TOURNAMENT_PAYLOAD)
    assert t.status_code == 201
    tournament_id = t.json()["id"]
    join_code = t.json()["join_code"]

    m = await client_user_1.post("/match", json={**MATCH_PAYLOAD, "tournament_id": tournament_id})
    assert m.status_code == 201
    match_id = m.json()["id"]

    join_resp = await client_user_2.post(f"/tournament/join/{join_code}")
    assert join_resp.status_code == 200

    # User 2 is participant — can predict and read
    resp = await client_user_2.post("/predict/match", json={"match_id": match_id, "home_score": 0, "away_score": 3})
    assert resp.status_code == 201
    assert resp.json()["home_score"] == 0
    assert resp.json()["away_score"] == 3

    resp = await client_user_2.get(f"/predict/match/{match_id}")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


# ===========================================================================
# Scoring: PredictTournament points_earned
# ===========================================================================

async def _setup_tournament_with_teams(client: AsyncClient):
    """Helper: create a tournament, three teams, and a future match. Returns ids."""
    t = await client.post(
        "/tournament",
        json={"name": "Scoring Test Tournament"},
    )
    assert t.status_code == 201
    tournament_id = t.json()["id"]

    team_a = await client.post("/team", json={**TEAM_PAYLOAD, "tournament_id": tournament_id})
    assert team_a.status_code == 201
    team_b = await client.post("/team", json={**TEAM_2_PAYLOAD, "tournament_id": tournament_id})
    assert team_b.status_code == 201
    team_c = await client.post("/team", json={**{**TEAM_PAYLOAD, "name": "Team Gamma", "iso_code": "ES"}, "tournament_id": tournament_id})
    assert team_c.status_code == 201

    # Future match so predictions are open
    m = await client.post("/match", json={**MATCH_PAYLOAD, "tournament_id": tournament_id})
    assert m.status_code == 201

    return tournament_id, team_a.json()["id"], team_b.json()["id"], team_c.json()["id"]


@pytest.mark.asyncio
async def test_scoring_tournament_correct_first_place(client_user_1: AsyncClient):
    """Predicting the first-place team earns first_place_points after tournament result is set."""
    tournament_id, team_a_id, team_b_id, _ = await _setup_tournament_with_teams(client_user_1)

    pred = await client_user_1.post("/predict/tournament", json={"tournament_id": tournament_id, "winner_team_id": team_a_id})
    assert pred.status_code == 201
    assert pred.json()["points_earned"] is None  # result not yet known

    patch = await client_user_1.patch(
        f"/tournament/{tournament_id}",
        json={"first_place_team_id": team_a_id, "second_place_team_id": team_b_id},
    )
    assert patch.status_code == 200

    resp = await client_user_1.get(f"/predict/tournament/{tournament_id}")
    assert resp.status_code == 200
    assert resp.json()[0]["points_earned"] == 25  # default first_place_points


@pytest.mark.asyncio
async def test_scoring_tournament_correct_second_place(client_user_1: AsyncClient):
    """Predicting the second-place team earns second_place_points."""
    tournament_id, team_a_id, team_b_id, _ = await _setup_tournament_with_teams(client_user_1)

    pred = await client_user_1.post("/predict/tournament", json={"tournament_id": tournament_id, "winner_team_id": team_b_id})
    assert pred.status_code == 201

    await client_user_1.patch(
        f"/tournament/{tournament_id}",
        json={"first_place_team_id": team_a_id, "second_place_team_id": team_b_id},
    )

    resp = await client_user_1.get(f"/predict/tournament/{tournament_id}")
    assert resp.status_code == 200
    assert resp.json()[0]["points_earned"] == 15  # default second_place_points


@pytest.mark.asyncio
async def test_scoring_tournament_correct_third_place(client_user_1: AsyncClient):
    """Predicting the third-place team earns third_place_points."""
    tournament_id, team_a_id, team_b_id, team_c_id = await _setup_tournament_with_teams(client_user_1)

    pred = await client_user_1.post("/predict/tournament", json={"tournament_id": tournament_id, "winner_team_id": team_c_id})
    assert pred.status_code == 201

    await client_user_1.patch(
        f"/tournament/{tournament_id}",
        json={"first_place_team_id": team_a_id, "second_place_team_id": team_b_id, "third_place_team_id": team_c_id, "third_place_points": 8},
    )

    resp = await client_user_1.get(f"/predict/tournament/{tournament_id}")
    assert resp.status_code == 200
    assert resp.json()[0]["points_earned"] == 8


@pytest.mark.asyncio
async def test_scoring_tournament_wrong_prediction(client_user_1: AsyncClient):
    """Predicting the wrong team earns 0 points once results are set."""
    tournament_id, team_a_id, team_b_id, team_c_id = await _setup_tournament_with_teams(client_user_1)

    # User predicts team_c but neither first nor second place will be team_c
    pred = await client_user_1.post("/predict/tournament", json={"tournament_id": tournament_id, "winner_team_id": team_c_id})
    assert pred.status_code == 201

    await client_user_1.patch(
        f"/tournament/{tournament_id}",
        json={"first_place_team_id": team_a_id, "second_place_team_id": team_b_id},
    )

    resp = await client_user_1.get(f"/predict/tournament/{tournament_id}")
    assert resp.status_code == 200
    assert resp.json()[0]["points_earned"] == 0


@pytest.mark.asyncio
async def test_scoring_tournament_no_winner_predicted(client_user_1: AsyncClient):
    """A prediction with no winner_team_id earns 0 once results are known."""
    tournament_id, team_a_id, team_b_id, _ = await _setup_tournament_with_teams(client_user_1)

    pred = await client_user_1.post("/predict/tournament", json={"tournament_id": tournament_id})
    assert pred.status_code == 201

    await client_user_1.patch(
        f"/tournament/{tournament_id}",
        json={"first_place_team_id": team_a_id, "second_place_team_id": team_b_id},
    )

    resp = await client_user_1.get(f"/predict/tournament/{tournament_id}")
    assert resp.status_code == 200
    assert resp.json()[0]["points_earned"] == 0


@pytest.mark.asyncio
async def test_scoring_tournament_results_cleared_resets_to_null(client_user_1: AsyncClient):
    """Clearing all placement team IDs resets points_earned back to NULL."""
    tournament_id, team_a_id, team_b_id, _ = await _setup_tournament_with_teams(client_user_1)

    pred = await client_user_1.post("/predict/tournament", json={"tournament_id": tournament_id, "winner_team_id": team_a_id})
    assert pred.status_code == 201

    # Set results → points calculated
    await client_user_1.patch(
        f"/tournament/{tournament_id}",
        json={"first_place_team_id": team_a_id, "second_place_team_id": team_b_id},
    )
    resp = await client_user_1.get(f"/predict/tournament/{tournament_id}")
    assert resp.json()[0]["points_earned"] == 25  # default first_place_points

    # Clear all placements → points should reset to NULL
    await client_user_1.patch(
        f"/tournament/{tournament_id}",
        json={"first_place_team_id": None, "second_place_team_id": None, "third_place_team_id": None},
    )
    resp = await client_user_1.get(f"/predict/tournament/{tournament_id}")
    assert resp.status_code == 200
    assert resp.json()[0]["points_earned"] is None


@pytest.mark.asyncio
async def test_scoring_tournament_multiple_users(client_user_1: AsyncClient, client_user_2: AsyncClient):
    """All users' predictions are updated when tournament results are set via the API."""
    tournament_id, team_a_id, team_b_id, team_c_id = await _setup_tournament_with_teams(client_user_1)
    join_code = (await client_user_1.get(f"/tournament/{tournament_id}")).json()["join_code"]

    join_resp = await client_user_2.post(f"/tournament/join/{join_code}")
    assert join_resp.status_code == 200

    # User 1 predicts the winner correctly; user 2 predicts wrong
    await client_user_1.post("/predict/tournament", json={"tournament_id": tournament_id, "winner_team_id": team_a_id})
    await client_user_2.post("/predict/tournament", json={"tournament_id": tournament_id, "winner_team_id": team_c_id})

    await client_user_1.patch(
        f"/tournament/{tournament_id}",
        json={"first_place_team_id": team_a_id, "second_place_team_id": team_b_id},
    )

    # Admin (user 1) reads both predictions
    resp1 = await client_user_1.get(f"/predict/tournament/{tournament_id}", params={"user_id": 1})
    assert resp1.status_code == 200
    assert resp1.json()[0]["points_earned"] == 25  # default first_place_points

    resp2 = await client_user_1.get(f"/predict/tournament/{tournament_id}", params={"user_id": 2})
    assert resp2.status_code == 200
    assert resp2.json()[0]["points_earned"] == 0


# ===========================================================================
# Scoring: PredictMatch points_earned
# ===========================================================================

# Future match — predictions accepted; admin can PATCH goals any time
SCORING_MATCH_PAYLOAD = {
    "start_datetime": "2030-06-10T15:00:00",
    "home_goals": None,
    "away_goals": None,
    "football_data_org_id": None,
}


async def _setup_match_scoring(client: AsyncClient):
    """Helper: create a tournament + future match. Returns (tournament_id, match_id)."""
    t = await client.post("/tournament", json={"name": "Match Scoring Tournament"})
    assert t.status_code == 201
    tournament_id = t.json()["id"]

    m = await client.post("/match", json={**SCORING_MATCH_PAYLOAD, "tournament_id": tournament_id})
    assert m.status_code == 201
    match_id = m.json()["id"]

    return tournament_id, match_id


@pytest.mark.asyncio
async def test_scoring_match_exact_score(client_user_1: AsyncClient):
    """Predicting the exact score earns match_score_points (default 5)."""
    tournament_id, match_id = await _setup_match_scoring(client_user_1)

    # Submit prediction before result is known — points should be NULL
    pred = await client_user_1.post("/predict/match", json={"match_id": match_id, "home_score": 2, "away_score": 1})
    assert pred.status_code == 201
    assert pred.json()["points_earned"] is None

    # Set the result (exact match)
    await client_user_1.patch(f"/match/{match_id}", json={"home_goals": 2, "away_goals": 1})

    resp = await client_user_1.get(f"/predict/match/{match_id}")
    assert resp.status_code == 200
    assert resp.json()[0]["points_earned"] == 5  # default match_score_points


@pytest.mark.asyncio
async def test_scoring_match_correct_winner_home(client_user_1: AsyncClient):
    """Predicting the correct home-win earns match_winner_points (default 3)."""
    tournament_id, match_id = await _setup_match_scoring(client_user_1)

    await client_user_1.post("/predict/match", json={"match_id": match_id, "home_score": 3, "away_score": 0})
    await client_user_1.patch(f"/match/{match_id}", json={"home_goals": 1, "away_goals": 0})

    resp = await client_user_1.get(f"/predict/match/{match_id}")
    assert resp.status_code == 200
    assert resp.json()[0]["points_earned"] == 3  # default match_winner_points


@pytest.mark.asyncio
async def test_scoring_match_correct_winner_draw(client_user_1: AsyncClient):
    """Predicting a draw correctly earns match_winner_points."""
    tournament_id, match_id = await _setup_match_scoring(client_user_1)

    await client_user_1.post("/predict/match", json={"match_id": match_id, "home_score": 1, "away_score": 1})
    await client_user_1.patch(f"/match/{match_id}", json={"home_goals": 0, "away_goals": 0})

    resp = await client_user_1.get(f"/predict/match/{match_id}")
    assert resp.status_code == 200
    assert resp.json()[0]["points_earned"] == 3


@pytest.mark.asyncio
async def test_scoring_match_wrong_prediction(client_user_1: AsyncClient):
    """Predicting the wrong outcome earns 0 points."""
    tournament_id, match_id = await _setup_match_scoring(client_user_1)

    await client_user_1.post("/predict/match", json={"match_id": match_id, "home_score": 2, "away_score": 0})
    await client_user_1.patch(f"/match/{match_id}", json={"home_goals": 0, "away_goals": 1})

    resp = await client_user_1.get(f"/predict/match/{match_id}")
    assert resp.status_code == 200
    assert resp.json()[0]["points_earned"] == 0


@pytest.mark.asyncio
async def test_scoring_match_no_score_predicted(client_user_1: AsyncClient):
    """A prediction with no scores earns 0 once the match result is known."""
    tournament_id, match_id = await _setup_match_scoring(client_user_1)

    await client_user_1.post("/predict/match", json={"match_id": match_id})
    await client_user_1.patch(f"/match/{match_id}", json={"home_goals": 1, "away_goals": 0})

    resp = await client_user_1.get(f"/predict/match/{match_id}")
    assert resp.status_code == 200
    assert resp.json()[0]["points_earned"] == 0


@pytest.mark.asyncio
async def test_scoring_match_goals_cleared_resets_to_null(client_user_1: AsyncClient):
    """Clearing match goals after scoring resets points_earned back to NULL."""
    tournament_id, match_id = await _setup_match_scoring(client_user_1)

    await client_user_1.post("/predict/match", json={"match_id": match_id, "home_score": 1, "away_score": 1})
    await client_user_1.patch(f"/match/{match_id}", json={"home_goals": 1, "away_goals": 1})

    resp = await client_user_1.get(f"/predict/match/{match_id}")
    assert resp.json()[0]["points_earned"] == 5  # exact score

    # Clear goals
    await client_user_1.patch(f"/match/{match_id}", json={"home_goals": None, "away_goals": None})

    resp = await client_user_1.get(f"/predict/match/{match_id}")
    assert resp.status_code == 200
    assert resp.json()[0]["points_earned"] is None


@pytest.mark.asyncio
async def test_scoring_match_winner_points_update(client_user_1: AsyncClient):
    """Changing match_winner_points on the tournament recalculates existing predictions."""
    tournament_id, match_id = await _setup_match_scoring(client_user_1)

    await client_user_1.post("/predict/match", json={"match_id": match_id, "home_score": 3, "away_score": 0})
    await client_user_1.patch(f"/match/{match_id}", json={"home_goals": 1, "away_goals": 0})  # home wins

    resp = await client_user_1.get(f"/predict/match/{match_id}")
    assert resp.json()[0]["points_earned"] == 3  # default match_winner_points

    # Admin changes match_winner_points
    await client_user_1.patch(f"/tournament/{tournament_id}", json={"match_winner_points": 7})

    resp = await client_user_1.get(f"/predict/match/{match_id}")
    assert resp.status_code == 200
    assert resp.json()[0]["points_earned"] == 7


@pytest.mark.asyncio
async def test_scoring_match_score_points_update(client_user_1: AsyncClient):
    """Changing match_score_points on the tournament recalculates existing predictions."""
    tournament_id, match_id = await _setup_match_scoring(client_user_1)

    await client_user_1.post("/predict/match", json={"match_id": match_id, "home_score": 2, "away_score": 1})
    await client_user_1.patch(f"/match/{match_id}", json={"home_goals": 2, "away_goals": 1})  # exact

    resp = await client_user_1.get(f"/predict/match/{match_id}")
    assert resp.json()[0]["points_earned"] == 5  # default match_score_points

    await client_user_1.patch(f"/tournament/{tournament_id}", json={"match_score_points": 10})

    resp = await client_user_1.get(f"/predict/match/{match_id}")
    assert resp.status_code == 200
    assert resp.json()[0]["points_earned"] == 10


# ===========================================================================
# Scoring: PredictGroup points_earned
# ===========================================================================

async def _setup_group_scoring(client: AsyncClient):
    """Helper: create tournament + group + team. Returns (tournament_id, group_id, team_id)."""
    t = await client.post("/tournament", json={"name": "Group Scoring Tournament"})
    assert t.status_code == 201
    tournament_id = t.json()["id"]

    g = await client.post("/group", json={"name": "Group A", "tournament_id": tournament_id})
    assert g.status_code == 201
    group_id = g.json()["id"]

    team = await client.post("/team", json={"name": "Team Alpha", "iso_code": "DE", "image_url": None, "football_data_org_id": None, "tournament_id": tournament_id})
    assert team.status_code == 201
    team_id = team.json()["id"]

    return tournament_id, group_id, team_id


@pytest.mark.asyncio
async def test_scoring_group_correct_winner(client_user_1: AsyncClient):
    """Predicting the correct group winner earns group_winner_points (default 8)."""
    tournament_id, group_id, team_id = await _setup_group_scoring(client_user_1)

    # Admin predicts for user 2 (bypasses timing check)
    pred = await client_user_1.post("/predict/group", params={"user_id": 2}, json={"group_id": group_id, "winner_team_id": team_id})
    assert pred.status_code == 201
    assert pred.json()["points_earned"] is None  # no winner set yet

    await client_user_1.patch(f"/group/{group_id}", json={"winner_team_id": team_id})

    resp = await client_user_1.get(f"/predict/group/{group_id}", params={"user_id": 2})
    assert resp.status_code == 200
    assert resp.json()[0]["points_earned"] == 8  # default group_winner_points


@pytest.mark.asyncio
async def test_scoring_group_wrong_winner(client_user_1: AsyncClient):
    """Predicting the wrong group winner earns 0 points."""
    tournament_id, group_id, team_id = await _setup_group_scoring(client_user_1)

    # Create a second team to use as the actual winner
    other = await client_user_1.post("/team", json={"name": "Team Beta", "iso_code": "FR", "image_url": None, "football_data_org_id": None, "tournament_id": tournament_id})
    other_id = other.json()["id"]

    await client_user_1.post("/predict/group", params={"user_id": 2}, json={"group_id": group_id, "winner_team_id": team_id})
    await client_user_1.patch(f"/group/{group_id}", json={"winner_team_id": other_id})  # different winner

    resp = await client_user_1.get(f"/predict/group/{group_id}", params={"user_id": 2})
    assert resp.status_code == 200
    assert resp.json()[0]["points_earned"] == 0


@pytest.mark.asyncio
async def test_scoring_group_winner_cleared(client_user_1: AsyncClient):
    """Clearing the group winner resets points_earned to NULL."""
    tournament_id, group_id, team_id = await _setup_group_scoring(client_user_1)

    await client_user_1.post("/predict/group", params={"user_id": 2}, json={"group_id": group_id, "winner_team_id": team_id})
    await client_user_1.patch(f"/group/{group_id}", json={"winner_team_id": team_id})

    resp = await client_user_1.get(f"/predict/group/{group_id}", params={"user_id": 2})
    assert resp.json()[0]["points_earned"] == 8

    await client_user_1.patch(f"/group/{group_id}", json={"winner_team_id": None})

    resp = await client_user_1.get(f"/predict/group/{group_id}", params={"user_id": 2})
    assert resp.status_code == 200
    assert resp.json()[0]["points_earned"] is None


@pytest.mark.asyncio
async def test_scoring_group_winner_points_update(client_user_1: AsyncClient):
    """Changing group_winner_points on the tournament recalculates existing predictions."""
    tournament_id, group_id, team_id = await _setup_group_scoring(client_user_1)

    await client_user_1.post("/predict/group", params={"user_id": 2}, json={"group_id": group_id, "winner_team_id": team_id})
    await client_user_1.patch(f"/group/{group_id}", json={"winner_team_id": team_id})

    resp = await client_user_1.get(f"/predict/group/{group_id}", params={"user_id": 2})
    assert resp.json()[0]["points_earned"] == 8  # default

    await client_user_1.patch(f"/tournament/{tournament_id}", json={"group_winner_points": 12})

    resp = await client_user_1.get(f"/predict/group/{group_id}", params={"user_id": 2})
    assert resp.status_code == 200
    assert resp.json()[0]["points_earned"] == 12


@pytest.mark.asyncio
async def test_scoring_group_team_reassignment(client_user_1: AsyncClient):
    """Moving a team to another group triggers recalculation for the old group."""
    t = await client_user_1.post("/tournament", json={"name": "Team Move Tournament"})
    tournament_id = t.json()["id"]

    g1 = await client_user_1.post("/group", json={"name": "Group A", "tournament_id": tournament_id})
    g2 = await client_user_1.post("/group", json={"name": "Group B", "tournament_id": tournament_id})
    group1_id, group2_id = g1.json()["id"], g2.json()["id"]

    team = await client_user_1.post("/team", json={"name": "Wanderer", "iso_code": "DE", "image_url": None, "football_data_org_id": None, "tournament_id": tournament_id})
    team_id = team.json()["id"]

    # Predict group 1 winner = team; set group 1 winner = team
    await client_user_1.post("/predict/group", params={"user_id": 2}, json={"group_id": group1_id, "winner_team_id": team_id})
    await client_user_1.patch(f"/group/{group1_id}", json={"winner_team_id": team_id})

    resp = await client_user_1.get(f"/predict/group/{group1_id}", params={"user_id": 2})
    assert resp.json()[0]["points_earned"] == 8

    # Move team to group 2 — triggers recalculation for group 1
    await client_user_1.patch(f"/team/{team_id}", json={"group_id": group2_id})

    # Group 1 winner_team_id unchanged → prediction still 8
    resp = await client_user_1.get(f"/predict/group/{group1_id}", params={"user_id": 2})
    assert resp.status_code == 200
    assert resp.json()[0]["points_earned"] == 8


# ===========================================================================
# Scoring: PredictStage points_earned
# ===========================================================================

async def _setup_stage_scoring(client: AsyncClient):
    """Helper: create tournament + stage + team. Returns (tournament_id, stage_id, team_id)."""
    t = await client.post("/tournament", json={"name": "Stage Scoring Tournament"})
    assert t.status_code == 201
    tournament_id = t.json()["id"]

    s = await client.post("/stage", json={"name": "Semi-finals", "tournament_id": tournament_id})
    assert s.status_code == 201
    stage_id = s.json()["id"]

    team = await client.post("/team", json={"name": "Team Alpha", "iso_code": "DE", "image_url": None, "football_data_org_id": None, "tournament_id": tournament_id})
    assert team.status_code == 201
    team_id = team.json()["id"]

    return tournament_id, stage_id, team_id


@pytest.mark.asyncio
async def test_scoring_stage_correct_winner(client_user_1: AsyncClient):
    """Predicting the correct stage winner earns stage_winner_points."""
    tournament_id, stage_id, team_id = await _setup_stage_scoring(client_user_1)

    # Set a non-zero stage_winner_points first
    await client_user_1.patch(f"/tournament/{tournament_id}", json={"stage_winner_points": 10})

    pred = await client_user_1.post("/predict/stage", params={"user_id": 2}, json={"stage_id": stage_id, "winner_team_id": team_id})
    assert pred.status_code == 201
    assert pred.json()["points_earned"] is None  # no winner set yet

    await client_user_1.patch(f"/stage/{stage_id}", json={"winner_team_id": team_id})

    resp = await client_user_1.get(f"/predict/stage/{stage_id}", params={"user_id": 2})
    assert resp.status_code == 200
    assert resp.json()[0]["points_earned"] == 10


@pytest.mark.asyncio
async def test_scoring_stage_wrong_winner(client_user_1: AsyncClient):
    """Predicting the wrong stage winner earns 0 points."""
    tournament_id, stage_id, team_id = await _setup_stage_scoring(client_user_1)
    await client_user_1.patch(f"/tournament/{tournament_id}", json={"stage_winner_points": 10})

    other = await client_user_1.post("/team", json={"name": "Team Beta", "iso_code": "FR", "image_url": None, "football_data_org_id": None, "tournament_id": tournament_id})
    other_id = other.json()["id"]

    await client_user_1.post("/predict/stage", params={"user_id": 2}, json={"stage_id": stage_id, "winner_team_id": team_id})
    await client_user_1.patch(f"/stage/{stage_id}", json={"winner_team_id": other_id})

    resp = await client_user_1.get(f"/predict/stage/{stage_id}", params={"user_id": 2})
    assert resp.status_code == 200
    assert resp.json()[0]["points_earned"] == 0


@pytest.mark.asyncio
async def test_scoring_stage_winner_points_update(client_user_1: AsyncClient):
    """Changing stage_winner_points on the tournament recalculates existing stage predictions."""
    tournament_id, stage_id, team_id = await _setup_stage_scoring(client_user_1)

    await client_user_1.post("/predict/stage", params={"user_id": 2}, json={"stage_id": stage_id, "winner_team_id": team_id})
    await client_user_1.patch(f"/stage/{stage_id}", json={"winner_team_id": team_id})

    # Default stage_winner_points is 0
    resp = await client_user_1.get(f"/predict/stage/{stage_id}", params={"user_id": 2})
    assert resp.json()[0]["points_earned"] == 0

    await client_user_1.patch(f"/tournament/{tournament_id}", json={"stage_winner_points": 15})

    resp = await client_user_1.get(f"/predict/stage/{stage_id}", params={"user_id": 2})
    assert resp.status_code == 200
    assert resp.json()[0]["points_earned"] == 15
