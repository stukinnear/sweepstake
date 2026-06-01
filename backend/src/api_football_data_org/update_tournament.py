import asyncio
import hashlib
from pathlib import Path

import requests
from datetime import datetime, timezone, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.tournaments.models import Tournament
from src.database import AsyncSessionLocal
from src.teams import models as team_models
from src.matches.models import Match
from src.config import settings
from src.logging_config import get_logger

logger = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"


async def update_tournaments(db: AsyncSession, football_data_org_id: int) -> None:
    url = f"https://api.football-data.org/v4/competitions/{football_data_org_id}/matches"
    headers = {"X-Auth-Token": settings.football_data_org_api_key}

    response = await asyncio.to_thread(requests.get, url, headers=headers, timeout=30)
    response.raise_for_status()
    data = response.json()
    data_hash = hashlib.md5(str(data).encode()).hexdigest()

    hash_file = _DATA_DIR / f"football_data_hash_{football_data_org_id}.txt"
    if hash_file.is_file() and hash_file.read_text().strip() == data_hash:
        logger.info("No changes detected for competition %s — skipping import.", football_data_org_id)
        return

    matches = data["matches"]
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    past_matches = [
        m for m in matches
        if m["status"] == "FINISHED"
        and datetime.fromisoformat(m["utcDate"].replace("Z", "+00:00")) >= cutoff
    ]
    upcoming_matches = [m for m in matches if m["status"] == "TIMED"]

    tournament_ids = await db.execute(
        select(Tournament.id)
        .where(Tournament.football_data_org_id == football_data_org_id)
    )
    tournament_ids = tournament_ids.scalars().all()

    for match in past_matches + upcoming_matches:
        match_football_data_org_id = match["id"]
        start_datetime = datetime.fromisoformat(match["utcDate"].replace("Z", "+00:00"))
        home_team = {
            "football_data_org_id": match["homeTeam"]["id"],
            "name": match["homeTeam"]["name"],
            "iso_code": match["homeTeam"]["tla"],
            "image_url": match["homeTeam"]["crest"],
            "group_name": match["group"],
            "stage_name": match["stage"],
        }
        away_team = {
            "football_data_org_id": match["awayTeam"]["id"],
            "name": match["awayTeam"]["name"],
            "iso_code": match["awayTeam"]["tla"],
            "image_url": match["awayTeam"]["crest"],
            "group_name": match["group"],
            "stage_name": match["stage"],
        }
        home_goals = match["score"]["fullTime"]["home"]
        away_goals = match["score"]["fullTime"]["away"]

        matched_home_team = await db.execute(
            select(team_models.Team)
            .where(team_models.Team.football_data_org_id == home_team["football_data_org_id"])
        )
        matched_home_team = matched_home_team.scalars().first()
        if not matched_home_team and match["homeTeam"]["id"]:
            # create team if it doesn't exist
            matched_home_team = team_models.Team(**home_team)
            db.add(matched_home_team)
            await db.flush()  # flush to get matched_home_team.id
        
        matched_away_team = await db.execute(
            select(team_models.Team)
            .where(team_models.Team.football_data_org_id == away_team["football_data_org_id"])
        )
        matched_away_team = matched_away_team.scalars().first()
        if not matched_away_team and match["awayTeam"]["id"]:
            # create team if it doesn't exist
            matched_away_team = team_models.Team(**away_team)
            db.add(matched_away_team)
            await db.flush()  # flush to get matched_away_team.id

        matched_matches = await db.execute(
            select(Match)
            .where(Match.football_data_org_id == match_football_data_org_id)
        )
        matched_matches = matched_matches.scalars().all()

        tmp_tournament_ids = tournament_ids.copy()

        # update existing matches
        for matched_match in matched_matches:
            if matched_match.tournament_id in tmp_tournament_ids:
                tmp_tournament_ids.remove(matched_match.tournament_id)
            matched_match.start_datetime = start_datetime
            matched_match.home_goals = home_goals
            matched_match.away_goals = away_goals
            matched_match.home_team_id = matched_home_team.id if matched_home_team is not None else None
            matched_match.away_team_id = matched_away_team.id if matched_away_team is not None else None
            
            logger.info("Updated match %s (%s): %s vs %s on %s", matched_match.id, football_data_org_id, home_team["name"], away_team["name"], start_datetime)
        
        # if match is missing from tournament add it
        for tournament_id in tmp_tournament_ids:
            new_match = Match(
                football_data_org_id=match_football_data_org_id,
                tournament_id=tournament_id,
                start_datetime=start_datetime,
                home_goals=home_goals,
                away_goals=away_goals,
                home_team_id=matched_home_team.id if matched_home_team is not None else None,
                away_team_id=matched_away_team.id if matched_away_team is not None else None,
            )
            db.add(new_match)

            logger.info("Added new match for tournament %s (%s): %s vs %s on %s", tournament_id, football_data_org_id, home_team["name"], away_team["name"], start_datetime)

    await db.commit()

    hash_file.write_text(data_hash)


if __name__ == "__main__":
    import sys
    from src.main import run_alembic_startup_workflow
    from src.scripts.load_test_data import load_test_data

    football_data_org_id = int(sys.argv[1]) if len(sys.argv) > 1 else 2000

    run_alembic_startup_workflow()

    async def _main():
        await load_test_data()
        async with AsyncSessionLocal() as db:
            await update_tournaments(db, football_data_org_id)

    asyncio.run(_main())