import logging

logger = logging.getLogger("predictions.scoring")
"""Point-calculation logic for predictions.

Functions here are called by CRUD layers whenever tournament results change.
They update the `points_earned` column on the relevant Predict* rows.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import AsyncSessionLocal

_session_factory = AsyncSessionLocal

from src.predictions.models import PredictTournament, PredictMatch, PredictGroup, PredictStage
from src.matches.models import Match
from src.groups_stages.models import Group, Stage
from src.tournaments.models import Tournament


# ---------------------------------------------------------------------------
# Tournament predictions
# ---------------------------------------------------------------------------

async def recalculate_tournament_points(db: AsyncSession, tournament_id: int) -> None:
    """Recalculate points_earned for every PredictTournament row in a tournament.

    Rules:
    - winner_team_id == first_place_team_id  → first_place_points
    - winner_team_id == second_place_team_id → second_place_points
    - winner_team_id == third_place_team_id  → third_place_points  (only when third_place_points is set)
    - any other prediction                   → 0
    - If first_place_team_id, second_place_team_id, and third_place_team_id are all NULL
      the results are not yet known; set points_earned to NULL.
    """
    tournament = await db.get(Tournament, tournament_id)
    if tournament is None:
        return

    results_known = any(
        tid is not None
        for tid in (
            tournament.first_place_team_id,
            tournament.second_place_team_id,
            tournament.third_place_team_id,
        )
    )

    predictions_result = await db.execute(
        select(PredictTournament).where(PredictTournament.tournament_id == tournament_id)
    )
    predictions = predictions_result.scalars().all()

    for prediction in predictions:
        if not results_known:
            prediction.points_earned = None
        elif prediction.winner_team_id is None:
            prediction.points_earned = 0
        elif prediction.winner_team_id == tournament.first_place_team_id:
            prediction.points_earned = tournament.first_place_points or 0
        elif prediction.winner_team_id == tournament.second_place_team_id:
            prediction.points_earned = tournament.second_place_points or 0
        elif (
            tournament.third_place_team_id is not None
            and prediction.winner_team_id == tournament.third_place_team_id
        ):
            prediction.points_earned = tournament.third_place_points or 0
        else:
            prediction.points_earned = 0

    await db.flush()
    logger.info(f"Recalculated tournament prediction points for tournament_id=%s", tournament_id)


# ---------------------------------------------------------------------------
# Match predictions
# ---------------------------------------------------------------------------

def _match_winner(home: int, away: int) -> str:
    """Return 'home', 'away', or 'draw' based on goals."""
    if home > away:
        return "home"
    elif away > home:
        return "away"
    return "draw"


def _compute_match_points(
    pred: PredictMatch,
    match: Match,
    tournament: Tournament,
) -> int | None:
    """Return points_earned for a single PredictMatch row.

    Rules (in priority order):
    - NULL   if match result is not yet known (home_goals or away_goals is NULL)
    - score  = match_score_points  if exact score matches
    - winner = match_winner_points if correct outcome (win/draw) matches
    - 0      otherwise
    """
    if match.home_goals is None or match.away_goals is None:
        return None

    match_winner_points = tournament.match_winner_points or 0
    match_score_points = tournament.match_score_points or 0

    if pred.home_score is None or pred.away_score is None:
        return 0

    if pred.home_score == match.home_goals and pred.away_score == match.away_goals:
        return match_score_points

    if _match_winner(pred.home_score, pred.away_score) == _match_winner(match.home_goals, match.away_goals):
        return match_winner_points

    return 0


async def recalculate_match_points(db: AsyncSession, match_id: int) -> None:
    """Recalculate points_earned for every PredictMatch row for a single match."""
    match = await db.get(Match, match_id)
    if match is None:
        return
    tournament = await db.get(Tournament, match.tournament_id)
    if tournament is None:
        return

    predictions_result = await db.execute(
        select(PredictMatch).where(PredictMatch.match_id == match_id)
    )


    for pred in predictions_result.scalars().all():
        pred.points_earned = _compute_match_points(pred, match, tournament)

    await db.flush()
    logger.info(f"Recalculated match prediction points for match_id=%s", match_id)


async def recalculate_all_match_points_for_tournament(db: AsyncSession, tournament_id: int) -> None:
    """Recalculate points_earned for every PredictMatch row in a tournament."""
    tournament = await db.get(Tournament, tournament_id)
    if tournament is None:
        return

    matches_result = await db.execute(
        select(Match).where(Match.tournament_id == tournament_id)
    )


    for match in matches_result.scalars().all():
        preds_result = await db.execute(
            select(PredictMatch).where(PredictMatch.match_id == match.id)
        )
        for pred in preds_result.scalars().all():
            pred.points_earned = _compute_match_points(pred, match, tournament)

    await db.flush()
    logger.info(f"Recalculated all match prediction points for tournament_id=%s", tournament_id)


# ---------------------------------------------------------------------------
# Group predictions
# ---------------------------------------------------------------------------

def _compute_group_points(
    pred: PredictGroup,
    group: Group,
    tournament: Tournament,
) -> int | None:
    """Return points_earned for a single PredictGroup row.

    - NULL  if group winner is not yet known
    - group_winner_points if predicted winner matches actual winner
    - 0     otherwise
    """
    if group.winner_team_id is None:
        return None
    group_winner_points = tournament.group_winner_points or 0
    if pred.winner_team_id == group.winner_team_id:
        return group_winner_points
    return 0


async def recalculate_group_points(db: AsyncSession, group_id: int) -> None:
    """Recalculate points_earned for every PredictGroup row for a single group."""
    group = await db.get(Group, group_id)
    if group is None:
        return
    tournament = await db.get(Tournament, group.tournament_id)
    if tournament is None:
        return

    preds_result = await db.execute(
        select(PredictGroup).where(PredictGroup.group_id == group_id)
    )


    for pred in preds_result.scalars().all():
        pred.points_earned = _compute_group_points(pred, group, tournament)

    await db.flush()
    logger.info(f"Recalculated group prediction points for group_id=%s", group_id)


async def recalculate_all_group_points_for_tournament(db: AsyncSession, tournament_id: int) -> None:
    """Recalculate points_earned for every PredictGroup row in a tournament."""
    tournament = await db.get(Tournament, tournament_id)
    if tournament is None:
        return

    groups_result = await db.execute(
        select(Group).where(Group.tournament_id == tournament_id)
    )


    for group in groups_result.scalars().all():
        preds_result = await db.execute(
            select(PredictGroup).where(PredictGroup.group_id == group.id)
        )
        for pred in preds_result.scalars().all():
            pred.points_earned = _compute_group_points(pred, group, tournament)

    await db.flush()
    logger.info(f"Recalculated all group prediction points for tournament_id=%s", tournament_id)


# ---------------------------------------------------------------------------
# Stage predictions
# ---------------------------------------------------------------------------

def _compute_stage_points(
    pred: PredictStage,
    stage: Stage,
    tournament: Tournament,
) -> int | None:
    """Return points_earned for a single PredictStage row.

    - NULL  if stage winner is not yet known
    - stage_winner_points if predicted winner matches actual winner
    - 0     otherwise
    """
    if stage.winner_team_id is None:
        return None
    stage_winner_points = tournament.stage_winner_points or 0
    if pred.winner_team_id == stage.winner_team_id:
        return stage_winner_points
    return 0


async def recalculate_stage_points(db: AsyncSession, stage_id: int) -> None:
    """Recalculate points_earned for every PredictStage row for a single stage."""
    stage = await db.get(Stage, stage_id)
    if stage is None:
        return
    tournament = await db.get(Tournament, stage.tournament_id)
    if tournament is None:
        return

    preds_result = await db.execute(
        select(PredictStage).where(PredictStage.stage_id == stage_id)
    )


    for pred in preds_result.scalars().all():
        pred.points_earned = _compute_stage_points(pred, stage, tournament)

    await db.flush()
    logger.info(f"Recalculated stage prediction points for stage_id=%s", stage_id)


async def recalculate_all_stage_points_for_tournament(db: AsyncSession, tournament_id: int) -> None:
    """Recalculate points_earned for every PredictStage row in a tournament."""
    tournament = await db.get(Tournament, tournament_id)
    if tournament is None:
        return

    stages_result = await db.execute(
        select(Stage).where(Stage.tournament_id == tournament_id)
    )


    for stage in stages_result.scalars().all():
        preds_result = await db.execute(
            select(PredictStage).where(PredictStage.stage_id == stage.id)
        )
        for pred in preds_result.scalars().all():
            pred.points_earned = _compute_stage_points(pred, stage, tournament)

    await db.flush()
    logger.info(f"Recalculated all stage prediction points for tournament_id=%s", tournament_id)


# ---------------------------------------------------------------------------
# Background-safe wrappers (own session + commit)
# ---------------------------------------------------------------------------

async def _run_in_new_session(func, *args) -> None:
    try:
        async with _session_factory() as db:
            await func(db, *args)
            await db.commit()
    except Exception:
        logger.exception("Background scoring task %s%s failed", func.__name__, args)


async def background_recalculate_match_points(match_id: int) -> None:
    await _run_in_new_session(recalculate_match_points, match_id)


async def background_recalculate_group_points(group_id: int) -> None:
    await _run_in_new_session(recalculate_group_points, group_id)


async def background_recalculate_stage_points(stage_id: int) -> None:
    await _run_in_new_session(recalculate_stage_points, stage_id)


async def background_recalculate_tournament_points(tournament_id: int) -> None:
    await _run_in_new_session(recalculate_tournament_points, tournament_id)


async def background_recalculate_all_match_points_for_tournament(tournament_id: int) -> None:
    await _run_in_new_session(recalculate_all_match_points_for_tournament, tournament_id)


async def background_recalculate_all_group_points_for_tournament(tournament_id: int) -> None:
    await _run_in_new_session(recalculate_all_group_points_for_tournament, tournament_id)


async def background_recalculate_all_stage_points_for_tournament(tournament_id: int) -> None:
    await _run_in_new_session(recalculate_all_stage_points_for_tournament, tournament_id)
