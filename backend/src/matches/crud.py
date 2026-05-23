from typing import Optional, List

from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.matches import models
from src.tournaments.models import TournamentAdminLink, TournamentParticipantLink
from src.predictions import scoring as predictions_scoring


async def is_participant_or_admin(db: AsyncSession, tournament_id: int, user_id: int) -> bool:
    """Return True if the user is a participant or admin of the given tournament."""
    result = await db.execute(
        select(TournamentParticipantLink).where(
            TournamentParticipantLink.tournament_id == tournament_id,
            TournamentParticipantLink.user_id == user_id,
        )
    )
    if result.scalar_one_or_none():
        return True
    result = await db.execute(
        select(TournamentAdminLink).where(
            TournamentAdminLink.tournament_id == tournament_id,
            TournamentAdminLink.user_id == user_id,
        )
    )
    return result.scalar_one_or_none() is not None


def _query_match():
    """Base select statement for querying matches with team relationships."""
    return (
        select(models.Match)
        .options(selectinload(models.Match.home_team))
        .options(selectinload(models.Match.away_team))
    )


async def create_match(db: AsyncSession, match: models.MatchCreate) -> models.Match:
    """Create a new match."""
    db_match = models.Match(**match.model_dump())
    db.add(db_match)
    await db.flush()
    await db.commit()
    return await get_match_by_id(db, db_match.id)


async def get_match_by_id(db: AsyncSession, match_id: int, refetch: bool = False) -> Optional[models.Match]:
    """Get a match by ID with team relationships loaded."""
    result = await db.execute(
        _query_match()
        .where(models.Match.id == match_id)
        .execution_options(populate_existing=refetch)
    )
    return result.scalar_one_or_none()


async def get_matches_by_tournament(
    db: AsyncSession, tournament_id: int
) -> List[models.Match]:
    """Get all matches for a tournament ordered by start time."""
    result = await db.execute(
        _query_match()
        .where(models.Match.tournament_id == tournament_id)
        .order_by(models.Match.start_datetime, models.Match.id)
    )
    return result.scalars().all()


async def update_match(
    db: AsyncSession, match_id: int, match_update: models.MatchUpdate,
    background_tasks: Optional[BackgroundTasks] = None,
) -> Optional[models.Match]:
    """Update a match."""
    db_match = await db.get(models.Match, match_id)
    if not db_match:
        return None

    _SCORING_FIELDS = {"home_goals", "away_goals", "home_team_id", "away_team_id"}

    update_data = match_update.model_dump(exclude_unset=True)
    recalculate = bool(_SCORING_FIELDS & update_data.keys())

    for field, value in update_data.items():
        setattr(db_match, field, value)

    await db.commit()
    if recalculate:
        if background_tasks is not None:
            background_tasks.add_task(predictions_scoring.background_recalculate_match_points, match_id)
        else:
            await predictions_scoring.background_recalculate_match_points(match_id)
    return await get_match_by_id(db, match_id, refetch=True)


async def delete_match(db: AsyncSession, match_id: int) -> Optional[models.Match]:
    """Delete a match."""
    db_match = await db.get(models.Match, match_id)
    if db_match:
        await db.delete(db_match)
        await db.commit()
    return db_match
