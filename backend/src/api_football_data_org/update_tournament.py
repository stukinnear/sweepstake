from sqlalchemy.ext.asyncio import AsyncSession

from src.providers import get_provider


async def update_tournaments(db: AsyncSession, football_data_org_id: int) -> None:
    await get_provider("football-data-org").update_competition(db, str(football_data_org_id))
