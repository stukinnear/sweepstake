from sqlalchemy.ext.asyncio import AsyncSession

from src.providers import get_provider
from src.tournaments import models as tournament_models


async def import_tournament(db: AsyncSession, competition_id: int, tournament: tournament_models.Tournament) -> tournament_models.Tournament:
    return await get_provider("football-data-org").import_competition(db, str(competition_id), tournament)
