from typing import Optional, List

from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.groups_stages import models
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


def _query_group():
    """Base select statement for querying groups with winner relationship."""
    return select(models.Group).options(selectinload(models.Group.winner))


def _query_stage():
    """Base select statement for querying stages with winner relationship."""
    return select(models.Stage).options(selectinload(models.Stage.winner))


# ============================================================================
# Group CRUD
# ============================================================================

async def create_group(db: AsyncSession, group: models.GroupCreate) -> models.Group:
    """Create a new group."""
    db_group = models.Group(**group.model_dump())
    db.add(db_group)
    await db.flush()
    await db.commit()
    return await get_group_by_id(db, db_group.id)


async def get_group_by_id(db: AsyncSession, group_id: int, refetch: bool = False) -> Optional[models.Group]:
    """Get a group by ID with winner relationship loaded."""
    result = await db.execute(
        _query_group()
        .where(models.Group.id == group_id)
        .execution_options(populate_existing=refetch)
    )
    return result.scalar_one_or_none()


async def get_groups_by_tournament(db: AsyncSession, tournament_id: int) -> List[models.Group]:
    """Get all groups for a tournament ordered alphabetically."""
    result = await db.execute(
        _query_group()
        .where(models.Group.tournament_id == tournament_id)
        .order_by(models.Group.name)
    )
    return result.scalars().all()


async def update_group(
    db: AsyncSession, group_id: int, group_update: models.GroupUpdate,
    background_tasks: Optional[BackgroundTasks] = None,
) -> Optional[models.Group]:
    """Update a group."""
    db_group = await db.get(models.Group, group_id)
    if not db_group:
        return None
    update_data = group_update.model_dump(exclude_unset=True)
    recalculate = "winner_team_id" in update_data
    for field, value in update_data.items():
        setattr(db_group, field, value)
    await db.commit()
    if recalculate:
        if background_tasks is not None:
            background_tasks.add_task(predictions_scoring.background_recalculate_group_points, group_id)
        else:
            await predictions_scoring.background_recalculate_group_points(group_id)
    return await get_group_by_id(db, group_id, refetch=True)


async def delete_group(db: AsyncSession, group_id: int) -> Optional[models.Group]:
    """Delete a group."""
    db_group = await db.get(models.Group, group_id)
    if db_group:
        await db.delete(db_group)
        await db.commit()
    return db_group


# ============================================================================
# Stage CRUD
# ============================================================================

async def create_stage(db: AsyncSession, stage: models.StageCreate) -> models.Stage:
    """Create a new stage."""
    db_stage = models.Stage(**stage.model_dump())
    db.add(db_stage)
    await db.flush()
    await db.commit()
    return await get_stage_by_id(db, db_stage.id)


async def get_stage_by_id(db: AsyncSession, stage_id: int, refetch: bool = False) -> Optional[models.Stage]:
    """Get a stage by ID with winner relationship loaded."""
    result = await db.execute(
        _query_stage()
        .where(models.Stage.id == stage_id)
        .execution_options(populate_existing=refetch)
    )
    return result.scalar_one_or_none()


async def get_stages_by_tournament(db: AsyncSession, tournament_id: int) -> List[models.Stage]:
    """Get all stages for a tournament ordered alphabetically."""
    result = await db.execute(
        _query_stage()
        .where(models.Stage.tournament_id == tournament_id)
        .order_by(models.Stage.name)
    )
    return result.scalars().all()


async def update_stage(
    db: AsyncSession, stage_id: int, stage_update: models.StageUpdate,
    background_tasks: Optional[BackgroundTasks] = None,
) -> Optional[models.Stage]:
    """Update a stage."""
    db_stage = await db.get(models.Stage, stage_id)
    if not db_stage:
        return None
    update_data = stage_update.model_dump(exclude_unset=True)
    recalculate = "winner_team_id" in update_data
    for field, value in update_data.items():
        setattr(db_stage, field, value)
    await db.commit()
    if recalculate:
        if background_tasks is not None:
            background_tasks.add_task(predictions_scoring.background_recalculate_stage_points, stage_id)
        else:
            await predictions_scoring.background_recalculate_stage_points(stage_id)
    return await get_stage_by_id(db, stage_id, refetch=True)


async def delete_stage(db: AsyncSession, stage_id: int) -> Optional[models.Stage]:
    """Delete a stage."""
    db_stage = await db.get(models.Stage, stage_id)
    if db_stage:
        await db.delete(db_stage)
        await db.commit()
    return db_stage
