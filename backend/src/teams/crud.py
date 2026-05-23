from typing import Optional, List

from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.teams import models
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


async def create_team(db: AsyncSession, team: models.TeamCreate) -> models.Team:
    """Create a new team."""
    db_team = models.Team(**team.model_dump())
    db.add(db_team)
    await db.commit()
    result = await db.execute(
        select(models.Team)
        .options(selectinload(models.Team.group))
        .where(models.Team.id == db_team.id)
        .execution_options(populate_existing=True)
    )
    return result.scalar_one()


async def get_team_by_id(db: AsyncSession, team_id: int, refetch: bool = False) -> Optional[models.Team]:
    """Get a team by ID."""
    result = await db.execute(
        select(models.Team)
        .where(models.Team.id == team_id)
        .execution_options(populate_existing=refetch)
    )
    return result.scalar_one_or_none()


async def get_teams_by_tournament(db: AsyncSession, tournament_id: int) -> List[models.Team]:
    """Get all teams for a tournament ordered alphabetically."""
    result = await db.execute(
        select(models.Team)
        .where(models.Team.tournament_id == tournament_id)
        .order_by(models.Team.name)
    )
    return result.scalars().all()


async def update_team(
    db: AsyncSession, team_id: int, team_update: models.TeamUpdate,
    background_tasks: Optional[BackgroundTasks] = None,
) -> Optional[models.Team]:
    """Update a team."""
    db_team = await db.get(models.Team, team_id)
    if not db_team:
        return None
    update_data = team_update.model_dump(exclude_unset=True)
    old_group_id = db_team.group_id if "group_id" in update_data else None
    for field, value in update_data.items():
        setattr(db_team, field, value)
    await db.commit()
    if "group_id" in update_data:
        if old_group_id is not None:
            if background_tasks is not None:
                background_tasks.add_task(predictions_scoring.background_recalculate_group_points, old_group_id)
            else:
                await predictions_scoring.background_recalculate_group_points(old_group_id)
        new_group_id = update_data["group_id"]
        if new_group_id is not None and new_group_id != old_group_id:
            if background_tasks is not None:
                background_tasks.add_task(predictions_scoring.background_recalculate_group_points, new_group_id)
            else:
                await predictions_scoring.background_recalculate_group_points(new_group_id)
    return await get_team_by_id(db, team_id, refetch=True)


async def delete_team(db: AsyncSession, team_id: int) -> Optional[models.Team]:
    """Delete a team."""
    db_team = await db.get(models.Team, team_id)
    if db_team:
        await db.delete(db_team)
        await db.commit()
    return db_team
