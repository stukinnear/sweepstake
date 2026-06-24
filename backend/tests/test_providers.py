from httpx import AsyncClient
import pytest

pytestmark = pytest.mark.asyncio


class FakeResponse:
    def __init__(self, data: dict):
        self._data = data

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._data


def _football_data_org_matches() -> dict:
    return {
        "competition": {"id": 2000, "name": "World Cup"},
        "matches": [
            {
                "id": 4001,
                "utcDate": "2026-06-11T19:00:00Z",
                "status": "TIMED",
                "group": "GROUP_A",
                "stage": "GROUP_STAGE",
                "homeTeam": {"id": 101, "name": "Alpha", "tla": "ALP", "crest": "https://example.com/alpha.png"},
                "awayTeam": {"id": 102, "name": "Beta", "tla": "BET", "crest": "https://example.com/beta.png"},
                "score": {"fullTime": {"home": None, "away": None}},
            },
            {
                "id": 4002,
                "utcDate": "2026-06-12T19:00:00Z",
                "status": "FINISHED",
                "group": "GROUP_A",
                "stage": "GROUP_STAGE",
                "homeTeam": {"id": 101, "name": "Alpha", "tla": "ALP", "crest": "https://example.com/alpha.png"},
                "awayTeam": {"id": 102, "name": "Beta", "tla": "BET", "crest": "https://example.com/beta.png"},
                "score": {"fullTime": {"home": 2, "away": 1}},
            },
        ],
    }


def _thesportsdb_events() -> dict:
    return {
        "events": [
            {
                "idEvent": "9001",
                "idLeague": "4330",
                "strLeague": "Scottish Premiership",
                "strSeason": "2026-2027",
                "strTimestamp": "2026-08-01T14:00:00+00:00",
                "strStatus": "Match Finished",
                "intRound": "1",
                "idHomeTeam": "201",
                "idAwayTeam": "202",
                "strHomeTeam": "Hearts",
                "strAwayTeam": "Hibs",
                "intHomeScore": "3",
                "intAwayScore": "2",
            }
        ]
    }


def _thesportsdb_teams() -> dict:
    return {
        "teams": [
            {"idTeam": "205", "strTeam": "Aberdeen", "strTeamShort": "ABE", "strBadge": "https://example.com/aberdeen.png"},
            {"idTeam": "201", "strTeam": "Heart of Midlothian", "strTeamShort": "HEA", "strBadge": "/images/media/team/badge/hearts.png"},
            {"idTeam": "202", "strTeam": "Hibernian", "strTeamShort": "HIB", "strBadge": "https://example.com/hibs.png"},
            {"idTeam": "206", "strTeam": "Dundee United", "strTeamShort": "DUN", "strBadge": "https://example.com/dundee-united.png"},
            {"idTeam": "207", "strTeam": "Falkirk", "strTeamShort": "FAL", "strBadge": "https://example.com/falkirk.png"},
            {"idTeam": "9901", "strTeam": "AFC Wimbledon", "strTeamShort": "WIM", "strBadge": "https://example.com/wimbledon.png"},
            {"idTeam": "208", "strTeam": "Kilmarnock", "strTeamShort": "KIL", "strBadge": "https://example.com/kilmarnock.png"},
            {"idTeam": "9902", "strTeam": "Barnsley", "strTeamShort": "BAR", "strBadge": "https://example.com/barnsley.png"},
            {"idTeam": "209", "strTeam": "Motherwell", "strTeamShort": "MOT", "strBadge": "https://example.com/motherwell.png"},
            {"idTeam": "210", "strTeam": "Rangers", "strTeamShort": "RAN", "strBadge": "https://example.com/rangers.png"},
            {"idTeam": "211", "strTeam": "St Johnstone", "strTeamShort": "STJ", "strBadge": "https://example.com/st-johnstone.png"},
            {"idTeam": "212", "strTeam": "St Mirren", "strTeamShort": "STM", "strBadge": "https://example.com/st-mirren.png"},
        ]
    }


async def test_import_football_data_org_provider_normalizes_data(client_user_1: AsyncClient, monkeypatch):
    def fake_get(url, **kwargs):
        assert "api.football-data.org" in url
        return FakeResponse(_football_data_org_matches())

    monkeypatch.setattr("src.providers.football_data_org.requests.get", fake_get)

    response = await client_user_1.post(
        "/providers/import/football-data-org/2000",
        json={"name": "Imported World Cup"},
    )

    assert response.status_code == 201
    tournament = response.json()
    assert tournament["external_provider"] == "football-data-org"
    assert tournament["external_id"] == "2000"

    teams = (await client_user_1.get(f"/team?tournament_id={tournament['id']}")).json()
    assert {team["external_id"] for team in teams} == {"101", "102"}
    assert all(team["external_provider"] == "football-data-org" for team in teams)
    assert {team["group_name"] for team in teams} == {"Group A"}

    matches = (await client_user_1.get(f"/match?tournament_id={tournament['id']}")).json()
    assert [match["external_id"] for match in matches] == ["4001", "4002"]
    assert matches[0]["stage_name"] == "Group Stage"
    assert matches[1]["home_goals"] == 2
    assert matches[1]["away_goals"] == 1


async def test_import_thesportsdb_provider_normalizes_scottish_premiership(client_user_1: AsyncClient, monkeypatch):
    def fake_get(url, params=None, **kwargs):
        if url.endswith("eventsseason.php"):
            assert params == {"id": "4330", "s": "2026-2027"}
            return FakeResponse(_thesportsdb_events())
        if url.endswith("lookup_all_teams.php"):
            assert params == {"id": "4330"}
            return FakeResponse(_thesportsdb_teams())
        if url.endswith("lookupteam.php") and params == {"id": "201"}:
            return FakeResponse({"teams": [{"idTeam": "201", "strTeam": "Heart of Midlothian", "strTeamShort": "HEA", "strBadge": "/images/media/team/badge/hearts.png"}]})
        if url.endswith("lookupteam.php") and params == {"id": "202"}:
            return FakeResponse({"teams": [{"idTeam": "202", "strTeam": "Hibernian", "strTeamShort": "HIB", "strBadge": None}]})
        if url.endswith("searchteams.php") and params == {"t": "Hibs"}:
            return FakeResponse({"teams": [{"idTeam": "202", "strTeam": "Hibernian", "strTeamShort": "HIB", "strBadge": "https://example.com/hibs.png"}]})
        if url.endswith("searchteams.php") and params == {"t": "Celtic"}:
            return FakeResponse({"teams": [{"idTeam": "203", "strTeam": "Celtic", "strTeamShort": "CEL", "strBadge": "https://example.com/celtic.png"}]})
        if url.endswith("searchteams.php") and params == {"t": "Dundee"}:
            return FakeResponse({"teams": [{"idTeam": "204", "strTeam": "Dundee", "strTeamShort": "DUN", "strBadge": "https://example.com/dundee.png"}]})
        raise AssertionError(f"Unexpected URL {url} params={params}")

    monkeypatch.setattr("src.providers.thesportsdb.requests.get", fake_get)

    response = await client_user_1.post(
        "/providers/import/thesportsdb/4330",
        json={"name": "Scottish Premiership 2026-2027"},
    )

    assert response.status_code == 201
    tournament = response.json()
    assert tournament["external_provider"] == "thesportsdb"
    assert tournament["external_id"] == "4330"

    teams = (await client_user_1.get(f"/team?tournament_id={tournament['id']}")).json()
    team_names = {team["name"] for team in teams}
    assert len(teams) == 12
    assert {"Celtic", "Dundee"}.issubset(team_names)
    assert "AFC Wimbledon" not in team_names
    assert "Barnsley" not in team_names
    assert {"203", "204"}.issubset({team["external_id"] for team in teams})
    assert any(team["image_url"] == "https://www.thesportsdb.com/images/media/team/badge/hearts.png" for team in teams)
    assert any(team["image_url"] == "https://example.com/hibs.png" for team in teams)
    assert any(team["image_url"] == "https://example.com/celtic.png" for team in teams)
    assert any(team["image_url"] == "https://example.com/dundee.png" for team in teams)

    matches = (await client_user_1.get(f"/match?tournament_id={tournament['id']}")).json()
    assert len(matches) == 1
    assert matches[0]["external_provider"] == "thesportsdb"
    assert matches[0]["external_id"] == "9001"
    assert matches[0]["home_goals"] == 3
    assert matches[0]["away_goals"] == 2
    assert matches[0]["stage_name"] is None


async def test_provider_diagnostics_reports_counts_and_warnings(client_user_1: AsyncClient):
    tournament_resp = await client_user_1.post("/tournament", json={"name": "Diagnostics SPFL"})
    tournament_id = tournament_resp.json()["id"]
    await client_user_1.patch(
        f"/tournament/{tournament_id}",
        json={"external_provider": "thesportsdb", "external_id": "4330"},
    )
    team_resp = await client_user_1.post(
        "/team",
        json={
            "name": "Aberdeen",
            "iso_code": "ABE",
            "image_url": "https://example.com/aberdeen.png",
            "external_provider": "thesportsdb",
            "external_id": "133638",
            "tournament_id": tournament_id,
        },
    )
    team_id = team_resp.json()["id"]
    await client_user_1.post(
        "/match",
        json={
            "tournament_id": tournament_id,
            "start_datetime": "2026-08-01T15:00:00Z",
            "home_team_id": team_id,
            "away_team_id": team_id,
            "external_provider": "thesportsdb",
            "external_id": "fixture-1",
        },
    )

    response = await client_user_1.get(f"/providers/diagnostics/{tournament_id}")

    assert response.status_code == 200
    diagnostics = response.json()
    assert diagnostics["provider"] == "thesportsdb"
    assert diagnostics["competition_id"] == "4330"
    assert diagnostics["configured_league_id"] == "4330"
    assert diagnostics["season"] == "2026-2027"
    assert diagnostics["team_count"] == 1
    assert diagnostics["match_count"] == 1
    assert "Scottish Premiership should have 12 teams; this tournament has 1." in diagnostics["warnings"]
