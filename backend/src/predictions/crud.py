from datetime import datetime, timezone
from typing import Optional, List

import sqlalchemy as sa
from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.predictions import models
from src.matches.models import Match
from src.groups_stages.models import Group, Stage
from src.teams.models import Team
from src.tournaments.models import TournamentAdminLink
from src.predictions import scoring as predictions_scoring


# ============================================================================
# Access control helpers
# ============================================================================

async def is_admin_of_tournament(db: AsyncSession, tournament_id: int, user_id: int) -> bool:
    """Return True if the user is an admin of the given tournament."""
    result = await db.execute(
        select(TournamentAdminLink).where(
            TournamentAdminLink.tournament_id == tournament_id,
            TournamentAdminLink.user_id == user_id,
        )
    )
    return result.scalar_one_or_none() is not None


async def get_tournament_start_datetime(db: AsyncSession, tournament_id: int) -> Optional[datetime]:
    """Return the earliest match start_datetime for a tournament."""
    result = await db.execute(
        select(sa.func.min(Match.start_datetime)).where(Match.tournament_id == tournament_id)
    )
    return result.scalar_one_or_none()


async def get_group_start_datetime(db: AsyncSession, group_id: int) -> Optional[datetime]:
    """Return the earliest match start_datetime for a group (via its teams)."""
    team_ids = select(Team.id).where(Team.group_id == group_id)
    result = await db.execute(
        select(sa.func.min(Match.start_datetime)).where(
            sa.or_(
                Match.home_team_id.in_(team_ids),
                Match.away_team_id.in_(team_ids),
            )
        )
    )
    return result.scalar_one_or_none()


async def get_stage_start_datetime(db: AsyncSession, stage_id: int) -> Optional[datetime]:
    """Return the earliest match start_datetime for a stage."""
    result = await db.execute(
        select(sa.func.min(Match.start_datetime)).where(Match.stage_id == stage_id)
    )
    return result.scalar_one_or_none()




def _query_predict_tournament():
    return select(models.PredictTournament).options(
        selectinload(models.PredictTournament.winner_team)
    )


async def upsert_predict_tournament(
    db: AsyncSession, data: models.PredictTournamentCreate, user_id: int
) -> models.PredictTournament:
    """Create or update the current user's tournament prediction."""
    existing = await db.get(models.PredictTournament, (data.tournament_id, user_id))
    if existing:
        existing.winner_team_id = data.winner_team_id
    else:
        existing = models.PredictTournament(
            tournament_id=data.tournament_id,
            user_id=user_id,
            winner_team_id=data.winner_team_id,
        )
        db.add(existing)
    await db.commit()
    result = await db.execute(
        _query_predict_tournament()
        .where(
            models.PredictTournament.tournament_id == data.tournament_id,
            models.PredictTournament.user_id == user_id,
        )
        .execution_options(populate_existing=True)
    )
    return result.scalar_one()


async def get_predict_tournaments_by_tournament(
    db: AsyncSession, tournament_id: int, user_id: Optional[int] = None
) -> List[models.PredictTournament]:
    """Get all user predictions for a tournament."""
    q = _query_predict_tournament().where(models.PredictTournament.tournament_id == tournament_id)
    if user_id is not None:
        q = q.where(models.PredictTournament.user_id == user_id)
    result = await db.execute(q)
    return result.scalars().all()


async def delete_predict_tournament(
    db: AsyncSession, tournament_id: int, user_id: int
) -> Optional[models.PredictTournament]:
    """Delete the current user's tournament prediction."""
    existing = await db.get(models.PredictTournament, (tournament_id, user_id))
    if existing:
        await db.delete(existing)
        await db.commit()
    return existing


# ============================================================================
# PredictGroup
# ============================================================================

def _query_predict_group():
    return select(models.PredictGroup).options(
        selectinload(models.PredictGroup.winner_team)
    )


async def upsert_predict_group(
    db: AsyncSession, data: models.PredictGroupCreate, user_id: int,
    background_tasks: Optional[BackgroundTasks] = None,
) -> models.PredictGroup:
    """Create or update the current user's group prediction."""
    existing = await db.get(models.PredictGroup, (data.group_id, user_id))
    if existing:
        existing.winner_team_id = data.winner_team_id
    else:
        existing = models.PredictGroup(
            group_id=data.group_id,
            user_id=user_id,
            winner_team_id=data.winner_team_id,
        )
        db.add(existing)
    await db.flush()
    await db.commit()
    if background_tasks is not None:
        background_tasks.add_task(predictions_scoring.background_recalculate_group_points, data.group_id)
    else:
        await predictions_scoring.background_recalculate_group_points(data.group_id)
    result = await db.execute(
        _query_predict_group()
        .where(
            models.PredictGroup.group_id == data.group_id,
            models.PredictGroup.user_id == user_id,
        )
        .execution_options(populate_existing=True)
    )
    return result.scalar_one()


async def get_predict_groups_by_group(
    db: AsyncSession, group_id: int, user_id: Optional[int] = None
) -> List[models.PredictGroup]:
    """Get all user predictions for a group."""
    q = _query_predict_group().where(models.PredictGroup.group_id == group_id)
    if user_id is not None:
        q = q.where(models.PredictGroup.user_id == user_id)
    result = await db.execute(q)
    return result.scalars().all()


async def get_predict_groups_by_tournament(
    db: AsyncSession, tournament_id: int, user_id: Optional[int] = None
) -> List[models.PredictGroup]:
    """Get all user predictions for all groups in a tournament."""
    q = (
        _query_predict_group()
        .join(Group, models.PredictGroup.group_id == Group.id)
        .where(Group.tournament_id == tournament_id)
    )
    if user_id is not None:
        q = q.where(models.PredictGroup.user_id == user_id)
    result = await db.execute(q)
    return result.scalars().all()


async def delete_predict_group(
    db: AsyncSession, group_id: int, user_id: int
) -> Optional[models.PredictGroup]:
    """Delete the current user's group prediction."""
    existing = await db.get(models.PredictGroup, (group_id, user_id))
    if existing:
        await db.delete(existing)
        await db.commit()
    return existing


# ============================================================================
# PredictStage
# ============================================================================

def _query_predict_stage():
    return select(models.PredictStage).options(
        selectinload(models.PredictStage.winner_team)
    )


async def upsert_predict_stage(
    db: AsyncSession, data: models.PredictStageCreate, user_id: int,
    background_tasks: Optional[BackgroundTasks] = None,
) -> models.PredictStage:
    """Create or update the current user's stage prediction."""
    existing = await db.get(models.PredictStage, (data.stage_id, user_id))
    if existing:
        existing.winner_team_id = data.winner_team_id
    else:
        existing = models.PredictStage(
            stage_id=data.stage_id,
            user_id=user_id,
            winner_team_id=data.winner_team_id,
        )
        db.add(existing)
    await db.flush()
    await db.commit()
    if background_tasks is not None:
        background_tasks.add_task(predictions_scoring.background_recalculate_stage_points, data.stage_id)
    else:
        await predictions_scoring.background_recalculate_stage_points(data.stage_id)
    result = await db.execute(
        _query_predict_stage()
        .where(
            models.PredictStage.stage_id == data.stage_id,
            models.PredictStage.user_id == user_id,
        )
        .execution_options(populate_existing=True)
    )
    return result.scalar_one()


async def get_predict_stages_by_stage(
    db: AsyncSession, stage_id: int, user_id: Optional[int] = None
) -> List[models.PredictStage]:
    """Get all user predictions for a stage."""
    q = _query_predict_stage().where(models.PredictStage.stage_id == stage_id)
    if user_id is not None:
        q = q.where(models.PredictStage.user_id == user_id)
    result = await db.execute(q)
    return result.scalars().all()


async def get_predict_stages_by_tournament(
    db: AsyncSession, tournament_id: int, user_id: Optional[int] = None
) -> List[models.PredictStage]:
    """Get all user predictions for all stages in a tournament."""
    q = (
        _query_predict_stage()
        .join(Stage, models.PredictStage.stage_id == Stage.id)
        .where(Stage.tournament_id == tournament_id)
    )
    if user_id is not None:
        q = q.where(models.PredictStage.user_id == user_id)
    result = await db.execute(q)
    return result.scalars().all()


async def delete_predict_stage(
    db: AsyncSession, stage_id: int, user_id: int
) -> Optional[models.PredictStage]:
    """Delete the current user's stage prediction."""
    existing = await db.get(models.PredictStage, (stage_id, user_id))
    if existing:
        await db.delete(existing)
        await db.commit()
    return existing


# ============================================================================
# PredictMatch
# ============================================================================

def _query_predict_match():
    return select(models.PredictMatch)


async def upsert_predict_match(
    db: AsyncSession, data: models.PredictMatchCreate, user_id: int,
    background_tasks: Optional[BackgroundTasks] = None,
) -> models.PredictMatch:
    """Create or update the current user's match prediction."""
    existing = await db.get(models.PredictMatch, (data.match_id, user_id))
    if existing:
        existing.home_score = data.home_score
        existing.away_score = data.away_score
    else:
        existing = models.PredictMatch(
            match_id=data.match_id,
            user_id=user_id,
            home_score=data.home_score,
            away_score=data.away_score,
        )
        db.add(existing)
    await db.flush()
    await db.commit()
    if background_tasks is not None:
        background_tasks.add_task(predictions_scoring.background_recalculate_match_points, data.match_id)
    else:
        await predictions_scoring.background_recalculate_match_points(data.match_id)
    await db.refresh(existing)
    return existing


async def get_predict_matches_by_match(
    db: AsyncSession, match_id: int, user_id: Optional[int] = None
) -> List[models.PredictMatch]:
    """Get all user predictions for a match."""
    q = _query_predict_match().where(models.PredictMatch.match_id == match_id)
    if user_id is not None:
        q = q.where(models.PredictMatch.user_id == user_id)
    result = await db.execute(q)
    return result.scalars().all()


async def get_predict_matches_by_tournament(
    db: AsyncSession, tournament_id: int, user_id: Optional[int] = None
) -> List[models.PredictMatch]:
    """Get all user predictions for all matches in a tournament."""
    q = (
        _query_predict_match()
        .join(Match, models.PredictMatch.match_id == Match.id)
        .where(Match.tournament_id == tournament_id)
    )
    if user_id is not None:
        q = q.where(models.PredictMatch.user_id == user_id)
    result = await db.execute(q)
    return result.scalars().all()


async def delete_predict_match(
    db: AsyncSession, match_id: int, user_id: int
) -> Optional[models.PredictMatch]:
    """Delete the current user's match prediction."""
    existing = await db.get(models.PredictMatch, (match_id, user_id))
    if existing:
        await db.delete(existing)
        await db.commit()
    return existing
