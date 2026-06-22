import asyncio
from datetime import datetime

import requests
from aiocache import cached
from sqlalchemy import false

from src.config import settings
from src.providers.base import FootballProvider
from src.providers.models import ProviderCompetition, ProviderMatch, ProviderTeam
from src.tournaments import models as tournament_models
from src.teams import models as team_models
from src.matches import models as match_models
from src.logging_config import get_logger

logger = get_logger(__name__)


class FootballDataOrgProvider(FootballProvider):
    provider_id = "football-data-org"

    @cached(ttl=60 * 60)
    async def list_competitions(self) -> list[ProviderCompetition]:
        url = "https://api.football-data.org/v4/competitions"
        headers = {"X-Auth-Token": settings.football_data_org_api_key}
        tier = settings.football_data_org_api_tier

        response = await asyncio.to_thread(requests.get, url, headers=headers, params={"plan": tier}, timeout=30)
        response.raise_for_status()
        data = response.json()

        today = datetime.now().strftime("%Y-%m-%d")
        competitions = [
            ProviderCompetition(
                id=str(competition["id"]),
                name=f'{competition["name"]} ({competition["currentSeason"]["startDate"][:4] if competition["currentSeason"] else "N/A"}-{competition["currentSeason"]["endDate"][:4] if competition["currentSeason"] else "N/A"}, {competition["area"]["name"]})',
                area=competition["area"]["name"],
                current_season_start=competition["currentSeason"]["startDate"] if competition["currentSeason"] else None,
                current_season_end=competition["currentSeason"]["endDate"] if competition["currentSeason"] else None,
                emblem_url=competition["emblem"],
                provider=self.provider_id,
            )
            for competition in data["competitions"]
            if (competition["currentSeason"]["endDate"] >= today if competition["currentSeason"] else True)
        ]
        competitions.sort(key=lambda item: item.name)
        competitions.sort(key=lambda item: item.current_season_end or "", reverse=True)
        logger.info("Pulled %s tournaments from football-data.org with API key level=%s", len(competitions), tier)
        return competitions

    async def fetch_matches(self, competition_id: str) -> tuple[dict, list[ProviderMatch]]:
        url = f"https://api.football-data.org/v4/competitions/{competition_id}/matches"
        headers = {"X-Auth-Token": settings.football_data_org_api_key}

        response = await asyncio.to_thread(requests.get, url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data, [self._normalize_match(match) for match in data["matches"]]

    def _normalize_match(self, match: dict) -> ProviderMatch:
        return ProviderMatch(
            external_id=str(match["id"]),
            start_datetime=datetime.fromisoformat(match["utcDate"].replace("Z", "+00:00")),
            status=match["status"],
            home_team=self._normalize_team(match["homeTeam"]),
            away_team=self._normalize_team(match["awayTeam"]),
            home_goals=match["score"]["fullTime"]["home"],
            away_goals=match["score"]["fullTime"]["away"],
            group_name=match["group"],
            stage_name=match["stage"],
        )

    def _normalize_team(self, team: dict) -> ProviderTeam | None:
        if team["id"] is None:
            return None
        return ProviderTeam(
            external_id=str(team["id"]),
            name=team["name"],
            iso_code=team.get("tla"),
            image_url=team.get("crest"),
        )

    def _legacy_tournament_filter(self, competition_id: str):
        return tournament_models.Tournament.football_data_org_id == int(competition_id) if str(competition_id).isdigit() else false()

    def _legacy_team_filter(self, external_id: str):
        return team_models.Team.football_data_org_id == int(external_id) if str(external_id).isdigit() else false()

    def _legacy_match_filter(self, external_id: str):
        return match_models.Match.football_data_org_id == int(external_id) if str(external_id).isdigit() else false()
