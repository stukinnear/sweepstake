import asyncio

import requests
from aiocache import cached
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from src.database import AsyncSessionLocal
from src.tournaments import crud as tournament_crud, models as tournament_models
from src.groups_stages import crud as groups_stages_crud, models as groups_stages_models
from src.teams import crud as team_crud, models as team_models
from src.matches import crud as match_crud, models as match_models
from src.config import settings
from src.logging_config import get_logger

logger = get_logger(__name__)


async def import_tournament(db: AsyncSession, competition_id: int, tournament: tournament_models.TournamentCreate) -> None:
    url = f"https://api.football-data.org/v4/competitions/{competition_id}/matches"
    headers = {"X-Auth-Token": settings.football_data_org_api_key}

    response = await asyncio.to_thread(requests.get, url, headers=headers, timeout=30)
    response.raise_for_status()
    data = response.json()

    competition = data["competition"]

    logger.info(f"Created tournament '{tournament.name}' with ID {tournament.id} for competition '{competition['name']}'")

    # Collect unique teams from all matches
    teams_seen: dict[int, dict] = {}
    groups_seen: dict[str, int] = {}
    for match in data["matches"]:
        group = None if match["group"] is None else match["group"].replace("_", " ").title()
        if group is not None and group not in groups_seen:
            created_group = await groups_stages_crud.create_group(db, groups_stages_models.GroupCreate(name=group, tournament_id=tournament.id))
            groups_seen[group] = created_group.id
            logger.info(f"Created group '{group}' with ID {groups_seen[group]} for tournament '{tournament.name}'")
        for side in ("homeTeam", "awayTeam"):
            team_raw = {**match[side], "group_id": groups_seen[group] if group is not None else None}
            if team_raw["id"] is not None and team_raw["id"] not in teams_seen:
                teams_seen[team_raw["id"]] = team_raw

    team_id_map: dict[int, int] = {}
    for fdorg_id, team_raw in teams_seen.items():
        team = await team_crud.create_team(
            db,
            team_models.TeamCreate(
                name=team_raw["name"],
                football_data_org_id=fdorg_id,
                iso_code=team_raw.get("tla"),
                image_url=team_raw.get("crest"),
                tournament_id=tournament.id,
                group_id=team_raw.get("group_id"),
            ),
        )
        team_id_map[fdorg_id] = team.id

        logger.info(f"Imported team {team.name} with football-data.org ID {fdorg_id}")

    stages_seen: dict[str, int] = {}
    for match in data["matches"]:
        home_fdorg_id = match["homeTeam"]["id"]
        away_fdorg_id = match["awayTeam"]["id"]
        stage = None if match["stage"] is None else match["stage"].replace("_", " ").title()
        if stage is not None and stage not in stages_seen:
            created_stage = await groups_stages_crud.create_stage(db, groups_stages_models.StageCreate(name=stage, tournament_id=tournament.id))
            stages_seen[stage] = created_stage.id
            logger.info(f"Created stage '{stage}' with ID {stages_seen[stage]} for tournament '{tournament.name}'")
        await match_crud.create_match(
            db,
            match_models.MatchCreate(
                football_data_org_id=match["id"],
                tournament_id=tournament.id,
                home_team_id=None if home_fdorg_id is None else team_id_map[home_fdorg_id],
                away_team_id=None if away_fdorg_id is None else team_id_map[away_fdorg_id],
                stage_id=stages_seen[stage] if stage is not None else None,
                start_datetime=match["utcDate"],
                home_goals=match["score"]["fullTime"]["home"],
                away_goals=match["score"]["fullTime"]["away"],
            ),
        )

        logger.info(f"Imported match {match['homeTeam']['name']} vs {match['awayTeam']['name']} on {match['utcDate']}")
    
    return tournament

