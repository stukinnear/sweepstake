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
        if url.endswith("lookupteam.php") and params == {"id": "201"}:
            return FakeResponse({"teams": [{"idTeam": "201", "strTeam": "Heart of Midlothian", "strTeamShort": "HEA", "strBadge": "/images/media/team/badge/hearts.png"}]})
        if url.endswith("lookupteam.php") and params == {"id": "202"}:
            return FakeResponse({"teams": [{"idTeam": "202", "strTeam": "Hibernian", "strTeamShort": "HIB", "strBadge": "https://example.com/hibs.png"}]})
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
    assert {team["name"] for team in teams} == {"Heart of Midlothian", "Hibernian"}
    assert {team["external_id"] for team in teams} == {"201", "202"}
    assert any(team["image_url"] == "https://www.thesportsdb.com/images/media/team/badge/hearts.png" for team in teams)

    matches = (await client_user_1.get(f"/match?tournament_id={tournament['id']}")).json()
    assert len(matches) == 1
    assert matches[0]["external_provider"] == "thesportsdb"
    assert matches[0]["external_id"] == "9001"
    assert matches[0]["home_goals"] == 3
    assert matches[0]["away_goals"] == 2
    assert matches[0]["stage_name"] == "1"
