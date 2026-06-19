"""Read-only aggregation queries for the stats module."""

from typing import Dict, List, Optional

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, nullslast
from sqlalchemy.orm import selectinload

from src.stats.models import (
    GroupStatsRead,
    LeaderboardEntry,
    MatchStatsRead,
    ParticipantActivityEntry,
    StageStatsRead,
    TournamentStatsRead,
    UserPredictionMatch,
    WinnerPredictionGroup,
    WinnerPredictionUser,
)
from src.teams.models import Team, TeamRead
from src.users.models import User
from src.tournaments.models import TournamentParticipantLink
from src.predictions.models import PredictGroup, PredictMatch, PredictStage, PredictTournament
from src.groups_stages.models import Group, Stage
from src.matches.models import Match
from src.matches.crud import get_match_by_id
from src.groups_stages.crud import get_group_by_id, get_stage_by_id
from src.tournaments.crud import get_tournament_by_id


async def _fetch_user_name_map(db: AsyncSession, user_ids: List[int]) -> Dict[int, str]:
    """Return {user_id: display_name} for the given IDs (user_name falling back to first_name)."""
    if not user_ids:
        return {}
    result = await db.execute(
        select(User.id, User.user_name, User.first_name).where(User.id.in_(user_ids))
    )
    return {row.id: (row.user_name or row.first_name) for row in result}


async def get_leaderboard(db: AsyncSession, tournament_id: int) -> List[LeaderboardEntry]:
    """Sum points_earned from all 4 prediction tables for each tournament participant.

    Participants with no scored predictions receive 0. Dense rank: ties share the same rank
    and the next distinct score gets the next sequential rank number.
    """
    t_pts = (
        select(PredictTournament.user_id, sa.func.sum(PredictTournament.points_earned).label("pts"))
        .where(PredictTournament.tournament_id == tournament_id)
        .group_by(PredictTournament.user_id)
        .subquery()
    )
    g_pts = (
        select(PredictGroup.user_id, sa.func.sum(PredictGroup.points_earned).label("pts"))
        .join(Group, PredictGroup.group_id == Group.id)
        .where(Group.tournament_id == tournament_id)
        .group_by(PredictGroup.user_id)
        .subquery()
    )
    s_pts = (
        select(PredictStage.user_id, sa.func.sum(PredictStage.points_earned).label("pts"))
        .join(Stage, PredictStage.stage_id == Stage.id)
        .where(Stage.tournament_id == tournament_id)
        .group_by(PredictStage.user_id)
        .subquery()
    )
    m_pts = (
        select(PredictMatch.user_id, sa.func.sum(PredictMatch.points_earned).label("pts"))
        .join(Match, PredictMatch.match_id == Match.id)
        .where(Match.tournament_id == tournament_id)
        .group_by(PredictMatch.user_id)
        .subquery()
    )

    total = (
        sa.func.coalesce(t_pts.c.pts, 0)
        + sa.func.coalesce(g_pts.c.pts, 0)
        + sa.func.coalesce(s_pts.c.pts, 0)
        + sa.func.coalesce(m_pts.c.pts, 0)
    ).label("total_points")

    q = (
        select(User.id, User.user_name, User.first_name, total)
        .join(
            TournamentParticipantLink,
            (TournamentParticipantLink.user_id == User.id)
            & (TournamentParticipantLink.tournament_id == tournament_id),
        )
        .outerjoin(t_pts, t_pts.c.user_id == User.id)
        .outerjoin(g_pts, g_pts.c.user_id == User.id)
        .outerjoin(s_pts, s_pts.c.user_id == User.id)
        .outerjoin(m_pts, m_pts.c.user_id == User.id)
        .order_by(
            sa.desc(total),
            nullslast(User.user_name.asc()),
            User.first_name.asc(),
        )
    )

    result = await db.execute(q)
    rows = result.all()

    entries: List[LeaderboardEntry] = []
    rank = 0
    prev_points = None
    for row in rows:
        if row.total_points != prev_points:
            rank += 1
            prev_points = row.total_points
        entries.append(
            LeaderboardEntry(
                rank=rank,
                user_id=row.id,
                user_name=row.user_name or row.first_name,
                total_points=row.total_points,
            )
        )
    return entries


async def get_match_stats(db: AsyncSession, match_id: int) -> MatchStatsRead:
    """Return all predictions for a match together with the actual score."""
    match = await get_match_by_id(db, match_id)

    result = await db.execute(
        select(PredictMatch, User.user_name, User.first_name)
        .join(User, PredictMatch.user_id == User.id)
        .where(PredictMatch.match_id == match_id)
    )
    rows = result.all()

    predictions = [
        UserPredictionMatch(
            user_id=pred.user_id,
            user_name=user_name or first_name,
            home_score=pred.home_score,
            away_score=pred.away_score,
            points_earned=pred.points_earned,
        )
        for pred, user_name, first_name in rows
    ]
    return MatchStatsRead(
        match_id=match_id,
        start_datetime=match.start_datetime,
        home_goals=match.home_goals,
        away_goals=match.away_goals,
        predictions=predictions,
    )


def _group_by_winner(preds, user_map: Dict[int, str]) -> List[WinnerPredictionGroup]:
    """Group predictions by winner_team, returning flattened WinnerPredictionGroup entries.

    Most-picked teams sort first; the no-prediction bucket (no team chosen) sorts last.
    """
    groups: Dict[Optional[int], WinnerPredictionGroup] = {}
    for p in preds:
        if p.winner_team_id not in groups:
            team_read = TeamRead.model_validate(p.winner_team, from_attributes=True) if p.winner_team else None
            team_fields = team_read.model_dump() if team_read else {}
            groups[p.winner_team_id] = WinnerPredictionGroup(**team_fields, users=[])
        groups[p.winner_team_id].users.append(
            WinnerPredictionUser(
                user_id=p.user_id,
                user_name=user_map.get(p.user_id),
                points_earned=p.points_earned,
            )
        )
    return sorted(groups.values(), key=lambda g: (g.id is None, -len(g.users)))


async def get_group_stats(db: AsyncSession, group_id: int) -> GroupStatsRead:
    """Return all predictions for a group grouped by predicted winner."""
    group = await get_group_by_id(db, group_id)

    pred_result = await db.execute(
        select(PredictGroup)
        .options(selectinload(PredictGroup.winner_team))
        .where(PredictGroup.group_id == group_id)
    )
    preds = pred_result.scalars().all()
    user_map = await _fetch_user_name_map(db, [p.user_id for p in preds])

    return GroupStatsRead(
        group_id=group_id,
        actual_winner_team_id=group.winner_team_id,
        actual_winner_team=TeamRead.model_validate(group.winner, from_attributes=True) if group.winner else None,
        predictions=_group_by_winner(preds, user_map),
    )


async def get_stage_stats(db: AsyncSession, stage_id: int) -> StageStatsRead:
    """Return all predictions for a stage grouped by predicted winner."""
    stage = await get_stage_by_id(db, stage_id)

    pred_result = await db.execute(
        select(PredictStage)
        .options(selectinload(PredictStage.winner_team))
        .where(PredictStage.stage_id == stage_id)
    )
    preds = pred_result.scalars().all()
    user_map = await _fetch_user_name_map(db, [p.user_id for p in preds])

    return StageStatsRead(
        stage_id=stage_id,
        actual_winner_team_id=stage.winner_team_id,
        actual_winner_team=TeamRead.model_validate(stage.winner, from_attributes=True) if stage.winner else None,
        predictions=_group_by_winner(preds, user_map),
    )


async def get_tournament_stats(db: AsyncSession, tournament_id: int) -> TournamentStatsRead:
    """Return all tournament-winner predictions together with the actual winner."""
    tournament = await get_tournament_by_id(db, tournament_id)

    pred_result = await db.execute(
        select(PredictTournament)
        .options(selectinload(PredictTournament.winner_team))
        .where(PredictTournament.tournament_id == tournament_id)
    )
    preds = pred_result.scalars().all()

    user_map = await _fetch_user_name_map(db, [p.user_id for p in preds])

    def _team(obj) -> Optional[TeamRead]:
        return TeamRead.model_validate(obj, from_attributes=True) if obj else None

    return TournamentStatsRead(
        tournament_id=tournament_id,
        first_place_team_id=tournament.first_place_team_id,
        first_place_team=_team(tournament.first_place),
        second_place_team_id=tournament.second_place_team_id,
        second_place_team=_team(tournament.second_place),
        third_place_team_id=tournament.third_place_team_id,
        third_place_team=_team(tournament.third_place),
        predictions=_group_by_winner(preds, user_map),
    )


async def get_participant_activity(
    db: AsyncSession, tournament_id: int
) -> List[ParticipantActivityEntry]:
    """Return prediction counts per participant for a tournament (all four prediction types)."""
    t_cnt = (
        select(PredictTournament.user_id, sa.func.count().label("cnt"))
        .where(PredictTournament.tournament_id == tournament_id)
        .group_by(PredictTournament.user_id)
        .subquery()
    )
    g_cnt = (
        select(PredictGroup.user_id, sa.func.count().label("cnt"))
        .join(Group, PredictGroup.group_id == Group.id)
        .where(Group.tournament_id == tournament_id)
        .group_by(PredictGroup.user_id)
        .subquery()
    )
    s_cnt = (
        select(PredictStage.user_id, sa.func.count().label("cnt"))
        .join(Stage, PredictStage.stage_id == Stage.id)
        .where(Stage.tournament_id == tournament_id)
        .group_by(PredictStage.user_id)
        .subquery()
    )
    m_cnt = (
        select(PredictMatch.user_id, sa.func.count().label("cnt"))
        .join(Match, PredictMatch.match_id == Match.id)
        .where(Match.tournament_id == tournament_id)
        .group_by(PredictMatch.user_id)
        .subquery()
    )

    q = (
        select(
            User.id,
            User.user_name,
            User.first_name,
            sa.func.coalesce(t_cnt.c.cnt, 0).label("tournament_predictions"),
            sa.func.coalesce(g_cnt.c.cnt, 0).label("group_predictions"),
            sa.func.coalesce(s_cnt.c.cnt, 0).label("stage_predictions"),
            sa.func.coalesce(m_cnt.c.cnt, 0).label("match_predictions"),
        )
        .join(
            TournamentParticipantLink,
            (TournamentParticipantLink.user_id == User.id)
            & (TournamentParticipantLink.tournament_id == tournament_id),
        )
        .outerjoin(t_cnt, t_cnt.c.user_id == User.id)
        .outerjoin(g_cnt, g_cnt.c.user_id == User.id)
        .outerjoin(s_cnt, s_cnt.c.user_id == User.id)
        .outerjoin(m_cnt, m_cnt.c.user_id == User.id)
        .order_by(nullslast(User.user_name.asc()), User.first_name.asc())
    )

    result = await db.execute(q)
    return [
        ParticipantActivityEntry(
            user_id=row.id,
            user_name=row.user_name or row.first_name,
            tournament_predictions=row.tournament_predictions,
            group_predictions=row.group_predictions,
            stage_predictions=row.stage_predictions,
            match_predictions=row.match_predictions,
        )
        for row in result.all()
    ]
