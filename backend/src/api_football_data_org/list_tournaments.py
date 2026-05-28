import asyncio
import requests, time
from datetime import datetime
from zoneinfo import ZoneInfo

from aiocache import cached
from src.config import settings
from src.logging_config import get_logger

logger = get_logger(__name__)


@cached(ttl=60*60)  # Cache for 1 hour
async def list_tournaments() -> list:
    url = "https://api.football-data.org/v4/competitions"
    headers = {"X-Auth-Token": settings.football_data_org_api_key}
    tier = settings.football_data_org_api_tier

    response = await asyncio.to_thread(requests.get, url, headers=headers, params={"plan": tier}, timeout=30)
    response.raise_for_status()
    data = response.json()

    today = datetime.now(ZoneInfo(settings.tz)).strftime("%Y-%m-%d")

    tournament_lst_formatted = [
        {
            "id": tournament["id"],
            "name": f'{tournament["name"]} ({tournament["currentSeason"]["startDate"][:4] if tournament["currentSeason"] else "N/A"}-{tournament["currentSeason"]["endDate"][:4] if tournament["currentSeason"] else "N/A"}, {tournament["area"]["name"]})',
            "area": tournament["area"]["name"],
            "current_season_start": tournament["currentSeason"]["startDate"] if tournament["currentSeason"] else None,
            "current_season_end": tournament["currentSeason"]["endDate"] if tournament["currentSeason"] else None,
            "emblem_url": tournament["emblem"],
        }
        for tournament in data["competitions"]
        if (tournament["currentSeason"]["endDate"] >= today if tournament["currentSeason"] else True)
    ]

    tournament_lst_formatted.sort(key=lambda x: x["name"])
    tournament_lst_formatted.sort(key=lambda x: x["current_season_end"] or "", reverse=True)

    logger.info(f"Pulled {len(tournament_lst_formatted)} tournaments from football-data.org with API key level={tier}")

    return tournament_lst_formatted

