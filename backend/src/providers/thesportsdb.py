import asyncio
from datetime import datetime, timezone

import requests
from aiocache import cached

from src.config import settings
from src.logging_config import get_logger
from src.providers.base import FootballProvider
from src.providers.models import ProviderCompetition, ProviderMatch, ProviderTeam

logger = get_logger(__name__)


class TheSportsDBProvider(FootballProvider):
    provider_id = "thesportsdb"

    def __init__(self) -> None:
        self._team_cache: dict[str, dict | None] = {}

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
        teams = await self._fetch_teams(team_ids)
        await self._fill_missing_teams_from_names(events, teams)
        return data, [self._normalize_match(event, teams) for event in events if event.get("idEvent")]

    async def _fetch_teams(self, team_ids: set[str]) -> dict[str, dict]:
        teams: dict[str, dict] = {}
        for team_id in team_ids:
            if team_id in self._team_cache:
                team = self._team_cache[team_id]
                if team:
                    teams[team_id] = team
                continue
            data = await self._get_json("lookupteam.php", {"id": team_id})
            team = (data.get("teams") or [None])[0]
            self._team_cache[team_id] = team
            if team:
                teams[team_id] = team
            logger.info(
                "TheSportsDB lookupteam id=%s name=%r badge=%s logo=%s",
                team_id,
                team.get("strTeam") if team else None,
                bool(team and team.get("strBadge")),
                bool(team and team.get("strLogo")),
            )
        return teams

    async def _fill_missing_teams_from_names(self, events: list[dict], teams: dict[str, dict]) -> None:
        for event in events:
            for side in ("Home", "Away"):
                team_id = event.get(f"id{side}Team")
                team_name = event.get(f"str{side}Team")
                existing_team = teams.get(team_id) if team_id else None
                if not team_name or (existing_team and self._team_image(existing_team)):
                    continue
                team = await self._search_team(team_name)
                if not team:
                    logger.info("TheSportsDB searchteams name=%r found no team", team_name)
                    continue
                cache_key = str(team_id or team.get("idTeam") or team_name)
                teams[cache_key] = team
                if team_id:
                    teams[team_id] = team
                logger.info(
                    "TheSportsDB searchteams name=%r matched=%r badge=%s logo=%s",
                    team_name,
                    team.get("strTeam"),
                    bool(team.get("strBadge")),
                    bool(team.get("strLogo")),
                )

    async def _search_team(self, team_name: str) -> dict | None:
        cache_key = f"name:{team_name.lower()}"
        if cache_key in self._team_cache:
            return self._team_cache[cache_key]
        data = await self._get_json("searchteams.php", {"t": team_name})
        teams = data.get("teams") or []
        exact_team = next(
            (
                team for team in teams
                if (team.get("strTeam") or "").casefold() == team_name.casefold()
            ),
            None,
        )
        team = exact_team or (teams[0] if teams else None)
        self._team_cache[cache_key] = team
        return team

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
        team_id = event.get(f"id{side}Team") or (team or {}).get("idTeam")
        team_name = (team or {}).get("strTeam") or event.get(f"str{side}Team")
        if not team_id and not team_name:
            return None
        return ProviderTeam(
            external_id=str(team_id or team_name),
            name=team_name or "TBD",
            iso_code=(team or {}).get("strTeamShort"),
            image_url=self._image_url(
                self._team_image(team or {})
            ),
        )

    def _team_image(self, team: dict) -> str | None:
        return (
            team.get("strBadge")
            or team.get("strLogo")
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
        if status in {"NS", "NOT STARTED", "SCHEDULED", "MATCH SCHEDULED", "TBD"}:
            return "TIMED"
        if "SCHEDULE" in status or "NOT START" in status:
            return "TIMED"
        if status:
            return status
        if event.get("intHomeScore") is not None and event.get("intAwayScore") is not None:
            return "FINISHED"
        return "TIMED"

    def _int_or_none(self, value):
        return None if value in (None, "") else int(value)
