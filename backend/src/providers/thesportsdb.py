import asyncio
from datetime import datetime, timezone

import requests
from aiocache import cached

from src.config import settings
from src.providers.base import FootballProvider
from src.providers.models import ProviderCompetition, ProviderMatch, ProviderTeam


class TheSportsDBProvider(FootballProvider):
    provider_id = "thesportsdb"

    @cached(ttl=60 * 60)
    async def list_competitions(self) -> list[ProviderCompetition]:
        return [
            ProviderCompetition(
                id=str(settings.thesportsdb_league_id),
                name=f"Scottish Premiership / Scottish Premier League ({settings.thesportsdb_season})",
                area="Scotland",
                current_season_start=settings.thesportsdb_season.split("-")[0],
                current_season_end=settings.thesportsdb_season.split("-")[-1],
                provider=self.provider_id,
            )
        ]

    async def fetch_matches(self, competition_id: str) -> tuple[dict, list[ProviderMatch]]:
        data = await self._get_json(
            "eventsseason.php",
            {"id": competition_id, "s": settings.thesportsdb_season},
        )
        events = data.get("events") or []
        team_ids = {event.get("idHomeTeam") for event in events if event.get("idHomeTeam")}
        team_ids.update(event.get("idAwayTeam") for event in events if event.get("idAwayTeam"))
        teams = await self._fetch_league_teams(competition_id)
        teams.update(await self._fetch_teams(team_ids - set(teams.keys())))
        await self._fetch_missing_team_images(events, teams)
        return data, [self._normalize_match(event, teams) for event in events if event.get("idEvent")]

    async def _fetch_league_teams(self, competition_id: str) -> dict[str, dict]:
        data = await self._get_json("lookup_all_teams.php", {"id": competition_id})
        return {
            str(team["idTeam"]): team
            for team in data.get("teams") or []
            if team.get("idTeam")
        }

    async def _fetch_teams(self, team_ids: set[str]) -> dict[str, dict]:
        teams: dict[str, dict] = {}
        for team_id in team_ids:
            data = await self._get_json("lookupteam.php", {"id": team_id})
            team = (data.get("teams") or [None])[0]
            if team:
                teams[team_id] = team
        return teams

    async def _fetch_missing_team_images(self, events: list[dict], teams: dict[str, dict]) -> None:
        for event in events:
            for side in ("Home", "Away"):
                team_id = event.get(f"id{side}Team")
                team_name = event.get(f"str{side}Team")
                if not team_id or not team_name:
                    continue
                team = teams.get(team_id) or {}
                if self._team_image(team):
                    continue
                search_data = await self._get_json("searchteams.php", {"t": team_name})
                matches = search_data.get("teams") or []
                found = next((item for item in matches if str(item.get("idTeam")) == str(team_id)), None)
                found = found or (matches[0] if matches else None)
                if found:
                    teams[team_id] = {**team, **found}

    async def _get_json(self, endpoint: str, params: dict[str, str]) -> dict:
        url = f"https://www.thesportsdb.com/api/v1/json/{settings.thesportsdb_api_key}/{endpoint}"
        response = await asyncio.to_thread(requests.get, url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()

    def _normalize_match(self, event: dict, teams: dict[str, dict]) -> ProviderMatch:
        home_team_id = event.get("idHomeTeam")
        away_team_id = event.get("idAwayTeam")
        return ProviderMatch(
            external_id=str(event["idEvent"]),
            start_datetime=self._parse_datetime(event),
            status=self._status(event),
            home_team=self._normalize_team(event, teams.get(home_team_id), "Home"),
            away_team=self._normalize_team(event, teams.get(away_team_id), "Away"),
            home_goals=self._int_or_none(event.get("intHomeScore")),
            away_goals=self._int_or_none(event.get("intAwayScore")),
            stage_name=event.get("strRound") or event.get("intRound"),
        )

    def _normalize_team(self, event: dict, team: dict | None, side: str) -> ProviderTeam | None:
        team_id = event.get(f"id{side}Team")
        if not team_id:
            return None
        return ProviderTeam(
            external_id=str(team_id),
            name=(team or {}).get("strTeam") or event.get(f"str{side}Team") or "TBD",
            iso_code=(team or {}).get("strTeamShort"),
            image_url=self._image_url(
                self._team_image(team or {})
                or event.get(f"str{side}TeamBadge")
                or event.get(f"str{side}TeamLogo")
            ),
        )

    def _team_image(self, team: dict) -> str | None:
        return (
            team.get("strBadge")
            or team.get("strTeamBadge")
            or team.get("strLogo")
            or team.get("strTeamLogo")
        )

    def _image_url(self, value: str | None) -> str | None:
        if not value:
            return None
        if value.startswith("//"):
            return f"https:{value}"
        if value.startswith("/"):
            return f"https://www.thesportsdb.com{value}"
        return value

    def _parse_datetime(self, event: dict) -> datetime:
        timestamp = event.get("strTimestamp")
        if timestamp:
            return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        date_value = event.get("dateEvent") or "1970-01-01"
        time_value = event.get("strTime") or "00:00:00"
        return datetime.fromisoformat(f"{date_value}T{time_value}").replace(tzinfo=timezone.utc)

    def _status(self, event: dict) -> str:
        status = (event.get("strStatus") or "").upper()
        if "FINISH" in status:
            return "FINISHED"
        if status in {"NS", "NOT STARTED", "SCHEDULED"}:
            return "TIMED"
        if status:
            return status
        if event.get("intHomeScore") is not None and event.get("intAwayScore") is not None:
            return "FINISHED"
        return "TIMED"

    def _int_or_none(self, value):
        return None if value in (None, "") else int(value)
