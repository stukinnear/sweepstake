"""Stats routes: leaderboard and per-event prediction summaries."""

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.exceptions import CustomError
from src.stats import crud, models
from src.matches.crud import get_match_by_id, is_participant_or_admin
from src.groups_stages.crud import get_group_by_id, get_stage_by_id
from src.predictions.crud import (
    get_group_start_datetime,
    get_stage_start_datetime,
    get_tournament_start_datetime,
)
from src.tournaments.crud import is_admin
from src.users.routers import verify_access_token

router = APIRouter(prefix="/stats", tags=["stats"])


def _require_started(start_dt: Optional[datetime]) -> None:
    """Raise 403 if start_dt is None (no matches) or still in the future."""
    if start_dt is None or start_dt.astimezone(timezone.utc) > datetime.now(timezone.utc):
        raise CustomError(
            "Access denied: predictions are hidden until the event starts",
            status_code=403,
        )


@router.get("/leaderboard/{tournament_id}", response_model=List[models.LeaderboardEntry])
async def get_leaderboard_endpoint(
    tournament_id: int = Path(..., description="Tournament ID", gt=0),
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Depends(verify_access_token),
):
    """
    Points leaderboard for a tournament.

    Returns a ranked list of all tournament participants ordered by total points descending,
    then alphabetically by display name. Points are summed across all four prediction types
    (tournament-winner, group-winner, stage-winner, match-score). Only scored predictions
    (non-NULL `points_earned`) contribute to the total; unscored predictions count as 0.

    Participants with equal points receive the same rank (dense ranking — no gaps).

    - **tournament_id**: ID of the tournament

    Accessible to tournament participants and admins at any time (no time gate).

    Returns **403** if the caller is not a participant or admin.
    """
    uid = token_payload["uid"]
    if not await is_participant_or_admin(db, tournament_id, uid):
        raise CustomError(
            "Forbidden: only participants and admins can view the leaderboard",
            status_code=403,
        )
    return await crud.get_leaderboard(db, tournament_id)


@router.get("/match/{match_id}", response_model=models.MatchStatsRead)
async def get_match_stats_endpoint(
    match_id: int = Path(..., description="Match ID", gt=0),
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Depends(verify_access_token),
):
    """
    All score predictions for a match, revealed after kick-off.

    Returns the actual match result (if available) and a flat list of every participant's
    score prediction for that match, including their earned points.

    - **match_id**: ID of the match
    - Response includes `start_datetime`, `home_goals` / `away_goals` (actual result, `null` if not yet played)
    - Each prediction entry contains `user_id`, `user_name`, `home_score`, `away_score`,
      and `points_earned` (`null` until the result is confirmed)

    Returns **403** if the caller is not a participant or admin, or if the match has not
    started yet (`start_datetime` is in the future or not set).
    Returns **404** if the match does not exist.
    """
    uid = token_payload["uid"]
    match = await get_match_by_id(db, match_id)
    if not match:
        raise CustomError("Match not found", status_code=404)
    if not await is_participant_or_admin(db, match.tournament_id, uid):
        raise CustomError(
            "Forbidden: only participants and admins can view match stats",
            status_code=403,
        )
    _require_started(match.start_datetime)
    return await crud.get_match_stats(db, match_id)


@router.get("/group/{group_id}", response_model=models.GroupStatsRead)
async def get_group_stats_endpoint(
    group_id: int = Path(..., description="Group ID", gt=0),
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Depends(verify_access_token),
):
    """
    All group-winner predictions, grouped by predicted team, revealed after the group stage starts.

    Returns the actual group winner (if decided) and predictions grouped by the team each
    participant picked. Each group entry contains the full team details (flattened) and a list
    of users who picked that team with their earned points. Groups are ordered by number of
    users descending; participants who made no prediction appear in a separate entry with
    `null` team fields.

    - **group_id**: ID of the group
    - `actual_winner_team_id` / `actual_winner_team`: the confirmed group winner (`null` if undecided)
    - Each prediction group: team fields (`id`, `name`, `iso_code`, `image_url`, …) + `users`
      list with `user_id`, `user_name`, and `points_earned`

    Start time is determined by the earliest match involving a team in this group.

    Returns **403** if the caller is not a participant or admin, or if the group stage has not
    started yet (`start_datetime` is in the future or no matches exist).
    Returns **404** if the group does not exist.
    """
    uid = token_payload["uid"]
    group = await get_group_by_id(db, group_id)
    if not group:
        raise CustomError("Group not found", status_code=404)
    if not await is_participant_or_admin(db, group.tournament_id, uid):
        raise CustomError(
            "Forbidden: only participants and admins can view group stats",
            status_code=403,
        )
    start_dt = await get_group_start_datetime(db, group_id)
    _require_started(start_dt)
    return await crud.get_group_stats(db, group_id)


@router.get("/stage/{stage_id}", response_model=models.StageStatsRead)
async def get_stage_stats_endpoint(
    stage_id: int = Path(..., description="Stage ID", gt=0),
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Depends(verify_access_token),
):
    """
    All stage-winner predictions, grouped by predicted team, revealed after the stage starts.

    Returns the actual stage winner (if decided) and predictions grouped by the team each
    participant picked. Each group entry contains the full team details (flattened) and a list
    of users who picked that team with their earned points. Groups are ordered by number of
    users descending; participants who made no prediction appear in a separate entry with
    `null` team fields.

    - **stage_id**: ID of the stage
    - `actual_winner_team_id` / `actual_winner_team`: the confirmed stage winner (`null` if undecided)
    - Each prediction group: team fields (`id`, `name`, `iso_code`, `image_url`, …) + `users`
      list with `user_id`, `user_name`, and `points_earned`

    Start time is determined by the earliest match in this stage.

    Returns **403** if the caller is not a participant or admin, or if the stage has not
    started yet (`start_datetime` is in the future or no matches exist).
    Returns **404** if the stage does not exist.
    """
    uid = token_payload["uid"]
    stage = await get_stage_by_id(db, stage_id)
    if not stage:
        raise CustomError("Stage not found", status_code=404)
    if not await is_participant_or_admin(db, stage.tournament_id, uid):
        raise CustomError(
            "Forbidden: only participants and admins can view stage stats",
            status_code=403,
        )
    start_dt = await get_stage_start_datetime(db, stage_id)
    _require_started(start_dt)
    return await crud.get_stage_stats(db, stage_id)


@router.get("/tournament/{tournament_id}", response_model=models.TournamentStatsRead)
async def get_tournament_stats_endpoint(
    tournament_id: int = Path(..., description="Tournament ID", gt=0),
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Depends(verify_access_token),
):
    """
    All tournament-winner predictions, grouped by predicted team, revealed after the tournament starts.

    Returns the confirmed first-, second-, and third-place teams (where known) and predictions
    grouped by the team each participant picked as tournament winner. Each group entry contains
    the full team details (flattened) and a list of users who picked that team with their earned
    points. Groups are ordered by number of users descending; participants who made no prediction
    appear in a separate entry with `null` team fields.

    - **tournament_id**: ID of the tournament
    - `first_place_team_id` / `first_place_team`: confirmed champion (`null` if undecided)
    - `second_place_team_id` / `second_place_team`: confirmed runner-up (`null` if undecided)
    - `third_place_team_id` / `third_place_team`: confirmed third place (`null` if undecided)
    - Each prediction group: team fields (`id`, `name`, `iso_code`, `image_url`, …) + `users`
      list with `user_id`, `user_name`, and `points_earned`

    Start time is determined by the earliest match in the tournament.

    Returns **403** if the caller is not a participant or admin, or if the tournament has not
    started yet (`start_datetime` is in the future or no matches exist).
    """
    uid = token_payload["uid"]
    if not await is_participant_or_admin(db, tournament_id, uid):
        raise CustomError(
            "Forbidden: only participants and admins can view tournament stats",
            status_code=403,
        )
    start_dt = await get_tournament_start_datetime(db, tournament_id)
    _require_started(start_dt)
    return await crud.get_tournament_stats(db, tournament_id)


@router.get("/participant-activity/{tournament_id}", response_model=List[models.ParticipantActivityEntry])
async def get_participant_activity_endpoint(
    tournament_id: int = Path(..., description="Tournament ID", gt=0),
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Depends(verify_access_token),
):
    """
    Prediction counts per participant, visible to tournament admins only.

    Returns one entry per participant showing how many predictions they have submitted
    across all four prediction types: tournament-winner, group-winner, stage-winner,
    and match-score. Useful for admins monitoring participation.

    - **tournament_id**: ID of the tournament

    Returns **403** if the caller is not a tournament admin.
    """
    uid = token_payload["uid"]
    if not await is_admin(db, tournament_id, uid):
        raise CustomError(
            "Forbidden: only tournament admins can view participant activity",
            status_code=403,
        )
    return await crud.get_participant_activity(db, tournament_id)
