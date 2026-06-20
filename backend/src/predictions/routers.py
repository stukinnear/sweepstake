"""Prediction routes: create/update, read, and delete for tournament, group, stage, and match predictions."""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, status, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.exceptions import CustomError
from src.predictions import crud, models
from src.matches.crud import is_participant_or_admin, get_match_by_id
from src.groups_stages.crud import get_group_by_id, get_stage_by_id
from src.users.routers import verify_access_token

predict_tournament_router = APIRouter(prefix="/predict/tournament", tags=["predictions"])
predict_group_router = APIRouter(prefix="/predict/group", tags=["predictions"])
predict_stage_router = APIRouter(prefix="/predict/stage", tags=["predictions"])
predict_match_router = APIRouter(prefix="/predict/match", tags=["predictions"])


async def _check_get_prediction_access(
    db: AsyncSession,
    tournament_id: int,
    token_user_id: int,
    target_user_id: int,
    start_dt: Optional[datetime],
) -> None:
    """Raise 403 if the token user may not view predictions for target_user_id.

    Allowed when any of the following hold:
    - Token user is an admin of the tournament.
    - Token user is viewing their own predictions.
    - Token user is a participant AND the referenced object has already started
      (start_date is today or in the past).
    """
    if not await is_participant_or_admin(db, tournament_id, token_user_id):
        raise CustomError("Forbidden: only participants and admins can view predictions", status_code=403)
    if await crud.is_admin_of_tournament(db, tournament_id, token_user_id):
        return
    if target_user_id == token_user_id:
        return
    # Participant viewing another user — only allowed once the object has started
    if start_dt is not None and start_dt.astimezone(timezone.utc).date() <= datetime.now(timezone.utc).date():
        return
    raise CustomError("Forbidden: cannot view other users' predictions before the event starts", status_code=403)


# ===========================================================================
# PredictTournament
# ===========================================================================

@predict_tournament_router.post("", response_model=models.PredictTournamentRead, status_code=status.HTTP_201_CREATED)
async def upsert_predict_tournament_endpoint(
    data: models.PredictTournamentCreate,
    user_id: Optional[int] = Query(None, description="User ID to make prediction for (admin only)", gt=0),
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Depends(verify_access_token),
):
    """
    Create or update a tournament winner prediction.

    - **tournament_id**: ID of the tournament to predict
    - **winner_team_id**: Optional team ID predicted to win the tournament
    - **user_id**: Optional target user ID (admin only; defaults to the token user)

    Returns the created or updated prediction.
    Admins may predict for other users. Participants may only predict before the tournament starts.
    """
    token_user_id = token_payload["uid"]
    target_user_id = user_id if user_id is not None else token_user_id
    if not await is_participant_or_admin(db, data.tournament_id, token_user_id):
        raise CustomError("Forbidden: only participants and admins can submit predictions", status_code=403)
    if await crud.is_admin_of_tournament(db, data.tournament_id, token_user_id) and target_user_id != token_user_id:
        pass  # admin editing another user's prediction
    elif target_user_id == token_user_id:
        predictions_open = await crud.get_tournament_predictions_open(db, data.tournament_id)
        if predictions_open == "closed":
            raise CustomError("Forbidden: predictions are closed for this tournament", status_code=403)
        elif predictions_open == "open":
            pass  # always allowed
        else:  # automatic
            start_dt = await crud.get_tournament_start_datetime(db, data.tournament_id)
            if start_dt is None or start_dt.astimezone(timezone.utc) <= datetime.now(timezone.utc):
                raise CustomError("Forbidden: predictions can only be submitted before the tournament starts", status_code=403)
    else:
        raise CustomError("Forbidden: predictions can only be submitted before the tournament starts or by admins", status_code=403)
    return await crud.upsert_predict_tournament(db, data, target_user_id)


@predict_tournament_router.get("/{tournament_id}", response_model=list[models.PredictTournamentRead])
async def get_predict_tournaments_endpoint(
    tournament_id: int = Path(..., description="Filter predictions by tournament ID", gt=0),
    user_id: Optional[int] = Query(None, description="Filter by user ID; defaults to the token user", gt=0),
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Depends(verify_access_token),
):
    """
    Retrieve tournament winner predictions for a tournament.

    - **tournament_id**: The tournament to retrieve predictions for (required)
    - **user_id**: Optionally filter by a specific user (defaults to the token user)

    Returns predictions for the given tournament filtered by user.
    Admins may view any user; participants may only view others' predictions once the tournament has started.
    """
    token_user_id = token_payload["uid"]
    target_user_id = user_id if user_id is not None else token_user_id
    start_dt = await crud.get_tournament_start_datetime(db, tournament_id)
    await _check_get_prediction_access(db, tournament_id, token_user_id, target_user_id, start_dt)
    return await crud.get_predict_tournaments_by_tournament(db, tournament_id, user_id=target_user_id)



# ===========================================================================
# PredictGroup
# ===========================================================================

@predict_group_router.post("", response_model=models.PredictGroupRead, status_code=status.HTTP_201_CREATED)
async def upsert_predict_group_endpoint(
    background_tasks: BackgroundTasks,
    data: models.PredictGroupCreate,
    user_id: Optional[int] = Query(None, description="User ID to make prediction for (admin only)", gt=0),
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Depends(verify_access_token),
):
    """
    Create or update a group winner prediction.

    - **group_id**: ID of the group to predict
    - **winner_team_id**: Optional team ID predicted to win the group
    - **user_id**: Optional target user ID (admin only; defaults to the token user)

    Returns the created or updated prediction.
    Admins may predict for other users. Participants may only predict before the group's first match.
    """
    token_user_id = token_payload["uid"]
    target_user_id = user_id if user_id is not None else token_user_id
    group = await get_group_by_id(db, data.group_id)
    if not group:
        raise CustomError("Group not found", status_code=404)
    if not await is_participant_or_admin(db, group.tournament_id, token_user_id):
        raise CustomError("Forbidden: only participants and admins can submit predictions", status_code=403)
    if await crud.is_admin_of_tournament(db, group.tournament_id, token_user_id) and target_user_id != token_user_id:
        pass  # admin editing another user's prediction
    elif target_user_id == token_user_id:
        predictions_open = await crud.get_tournament_predictions_open(db, group.tournament_id)
        if predictions_open == "closed":
            raise CustomError("Forbidden: predictions are closed for this tournament", status_code=403)
        elif predictions_open == "open":
            pass  # always allowed
        else:  # automatic
            start_dt = await crud.get_group_start_datetime(db, data.group_id)
            if start_dt is None or start_dt.astimezone(timezone.utc) <= datetime.now(timezone.utc):
                raise CustomError("Forbidden: predictions can only be submitted before the group starts", status_code=403)
    else:
        raise CustomError("Forbidden: predictions can only be submitted before the group starts or by admins", status_code=403)
    return await crud.upsert_predict_group(db, data, target_user_id, background_tasks)


@predict_group_router.get("", response_model=list[models.PredictGroupRead])
async def get_predict_groups_by_tournament_endpoint(
    tournament_id: int = Query(..., description="Filter predictions by tournament ID", gt=0),
    user_id: Optional[int] = Query(None, description="Filter by user ID; defaults to the token user", gt=0),
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Depends(verify_access_token),
):
    """
    Retrieve group winner predictions for all groups in a tournament.

    - **tournament_id**: The tournament to retrieve predictions for (required)
    - **user_id**: Optionally filter by a specific user (defaults to the token user)

    Returns predictions for all groups in the tournament filtered by user.
    Admins may view any user; participants may only view others' predictions once the tournament has started.
    """
    token_user_id = token_payload["uid"]
    target_user_id = user_id if user_id is not None else token_user_id
    start_dt = await crud.get_tournament_start_datetime(db, tournament_id)
    await _check_get_prediction_access(db, tournament_id, token_user_id, target_user_id, start_dt)
    return await crud.get_predict_groups_by_tournament(db, tournament_id, user_id=target_user_id)


@predict_group_router.get("/{group_id}", response_model=list[models.PredictGroupRead])
async def get_predict_groups_endpoint(
    group_id: int = Path(..., description="Filter predictions by group ID", gt=0),
    user_id: Optional[int] = Query(None, description="Filter by user ID; defaults to the token user", gt=0),
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Depends(verify_access_token),
):
    """
    Retrieve group winner predictions for a group.

    - **group_id**: The group to retrieve predictions for (required)
    - **user_id**: Optionally filter by a specific user (defaults to the token user)

    Returns predictions for the given group filtered by user.
    Admins may view any user; participants may only view others' predictions once the group has started.
    """
    token_user_id = token_payload["uid"]
    target_user_id = user_id if user_id is not None else token_user_id
    group = await get_group_by_id(db, group_id)
    if not group:
        raise CustomError("Group not found", status_code=404)
    start_dt = await crud.get_group_start_datetime(db, group_id)
    await _check_get_prediction_access(db, group.tournament_id, token_user_id, target_user_id, start_dt)
    return await crud.get_predict_groups_by_group(db, group_id, user_id=target_user_id)



# ===========================================================================
# PredictStage
# ===========================================================================

@predict_stage_router.post("", response_model=models.PredictStageRead, status_code=status.HTTP_201_CREATED)
async def upsert_predict_stage_endpoint(
    background_tasks: BackgroundTasks,
    data: models.PredictStageCreate,
    user_id: Optional[int] = Query(None, description="User ID to make prediction for (admin only)", gt=0),
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Depends(verify_access_token),
):
    """
    Create or update a stage winner prediction.

    - **stage_id**: ID of the stage to predict
    - **winner_team_id**: Optional team ID predicted to win the stage
    - **user_id**: Optional target user ID (admin only; defaults to the token user)

    Returns the created or updated prediction.
    Admins may predict for other users. Participants may only predict before the stage's first match.
    """
    token_user_id = token_payload["uid"]
    target_user_id = user_id if user_id is not None else token_user_id
    stage = await get_stage_by_id(db, data.stage_id)
    if not stage:
        raise CustomError("Stage not found", status_code=404)
    if not await is_participant_or_admin(db, stage.tournament_id, token_user_id):
        raise CustomError("Forbidden: only participants and admins can submit predictions", status_code=403)
    if await crud.is_admin_of_tournament(db, stage.tournament_id, token_user_id) and target_user_id != token_user_id:
        pass  # admin editing another user's prediction
    elif target_user_id == token_user_id:
        predictions_open = await crud.get_tournament_predictions_open(db, stage.tournament_id)
        if predictions_open == "closed":
            raise CustomError("Forbidden: predictions are closed for this tournament", status_code=403)
        elif predictions_open == "open":
            pass  # always allowed
        else:  # automatic
            start_dt = await crud.get_stage_start_datetime(db, data.stage_id)
            if start_dt is None or start_dt.astimezone(timezone.utc) <= datetime.now(timezone.utc):
                raise CustomError("Forbidden: predictions can only be submitted before the stage starts", status_code=403)
    else:
        raise CustomError("Forbidden: predictions can only be submitted before the stage starts or by admins", status_code=403)
    return await crud.upsert_predict_stage(db, data, target_user_id, background_tasks)


@predict_stage_router.get("", response_model=list[models.PredictStageRead])
async def get_predict_stages_by_tournament_endpoint(
    tournament_id: int = Query(..., description="Filter predictions by tournament ID", gt=0),
    user_id: Optional[int] = Query(None, description="Filter by user ID; defaults to the token user", gt=0),
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Depends(verify_access_token),
):
    """
    Retrieve stage winner predictions for all stages in a tournament.

    - **tournament_id**: The tournament to retrieve predictions for (required)
    - **user_id**: Optionally filter by a specific user (defaults to the token user)

    Returns predictions for all stages in the tournament filtered by user.
    Admins may view any user; participants may only view others' predictions once the tournament has started.
    """
    token_user_id = token_payload["uid"]
    target_user_id = user_id if user_id is not None else token_user_id
    start_dt = await crud.get_tournament_start_datetime(db, tournament_id)
    await _check_get_prediction_access(db, tournament_id, token_user_id, target_user_id, start_dt)
    return await crud.get_predict_stages_by_tournament(db, tournament_id, user_id=target_user_id)


@predict_stage_router.get("/{stage_id}", response_model=list[models.PredictStageRead])
async def get_predict_stages_endpoint(
    stage_id: int = Path(..., description="Filter predictions by stage ID", gt=0),
    user_id: Optional[int] = Query(None, description="Filter by user ID; defaults to the token user", gt=0),
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Depends(verify_access_token),
):
    """
    Retrieve stage winner predictions for a stage.

    - **stage_id**: The stage to retrieve predictions for (required)
    - **user_id**: Optionally filter by a specific user (defaults to the token user)

    Returns predictions for the given stage filtered by user.
    Admins may view any user; participants may only view others' predictions once the stage has started.
    """
    token_user_id = token_payload["uid"]
    target_user_id = user_id if user_id is not None else token_user_id
    stage = await get_stage_by_id(db, stage_id)
    if not stage:
        raise CustomError("Stage not found", status_code=404)
    start_dt = await crud.get_stage_start_datetime(db, stage_id)
    await _check_get_prediction_access(db, stage.tournament_id, token_user_id, target_user_id, start_dt)
    return await crud.get_predict_stages_by_stage(db, stage_id, user_id=target_user_id)


# ===========================================================================
# PredictMatch
# ===========================================================================

@predict_match_router.post("", response_model=models.PredictMatchRead, status_code=status.HTTP_201_CREATED)
async def upsert_predict_match_endpoint(
    background_tasks: BackgroundTasks,
    data: models.PredictMatchCreate,
    user_id: Optional[int] = Query(None, description="User ID to make prediction for (admin only)", gt=0),
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Depends(verify_access_token),
):
    """
    Create or update a match score prediction.

    - **match_id**: ID of the match to predict
    - **home_score**: Predicted home team goals (optional)
    - **away_score**: Predicted away team goals (optional)
    - **user_id**: Optional target user ID (admin only; defaults to the token user)

    Returns the created or updated prediction.
    Admins may predict for other users. Participants may only predict before the match starts.
    """
    token_user_id = token_payload["uid"]
    target_user_id = user_id if user_id is not None else token_user_id
    match = await get_match_by_id(db, data.match_id)
    if not match:
        raise CustomError("Match not found", status_code=404)
    if not await is_participant_or_admin(db, match.tournament_id, token_user_id):
        raise CustomError("Forbidden: only participants and admins can submit predictions", status_code=403)
    if await crud.is_admin_of_tournament(db, match.tournament_id, token_user_id) and target_user_id != token_user_id:
        pass  # admin editing another user's prediction
    elif target_user_id == token_user_id:
        if match.start_datetime is None or match.start_datetime.astimezone(timezone.utc) <= datetime.now(timezone.utc):
            raise CustomError("Forbidden: predictions can only be submitted before the match starts", status_code=403)
    else:
        raise CustomError("Forbidden: predictions can only be submitted before the match starts or by admins", status_code=403)
    return await crud.upsert_predict_match(db, data, target_user_id, background_tasks)


@predict_match_router.get("", response_model=list[models.PredictMatchRead])
async def get_predict_matches_by_tournament_endpoint(
    tournament_id: int = Query(..., description="Filter predictions by tournament ID", gt=0),
    user_id: Optional[int] = Query(None, description="Filter by user ID; defaults to the token user", gt=0),
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Depends(verify_access_token),
):
    """
    Retrieve match score predictions for all matches in a tournament.

    - **tournament_id**: The tournament to retrieve predictions for (required)
    - **user_id**: Optionally filter by a specific user (defaults to the token user)

    Returns predictions for all matches in the tournament filtered by user.
    Admins may view any user; participants may only view others' predictions once the tournament has started.
    """
    token_user_id = token_payload["uid"]
    target_user_id = user_id if user_id is not None else token_user_id
    start_dt = await crud.get_tournament_start_datetime(db, tournament_id)
    await _check_get_prediction_access(db, tournament_id, token_user_id, target_user_id, start_dt)
    return await crud.get_predict_matches_by_tournament(db, tournament_id, user_id=target_user_id)


@predict_match_router.get("/{match_id}", response_model=list[models.PredictMatchRead])
async def get_predict_matches_endpoint(
    match_id: int = Path(..., description="Filter predictions by match ID", gt=0),
    user_id: Optional[int] = Query(None, description="Filter by user ID; defaults to the token user", gt=0),
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Depends(verify_access_token),
):
    """
    Retrieve match score predictions for a match.

    - **match_id**: The match to retrieve predictions for (required)
    - **user_id**: Optionally filter by a specific user (defaults to the token user)

    Returns predictions for the given match filtered by user.
    Admins may view any user; participants may only view others' predictions once the match has started.
    """
    token_user_id = token_payload["uid"]
    target_user_id = user_id if user_id is not None else token_user_id
    match = await get_match_by_id(db, match_id)
    if not match:
        raise CustomError("Match not found", status_code=404)
    await _check_get_prediction_access(db, match.tournament_id, token_user_id, target_user_id, match.start_datetime)
    return await crud.get_predict_matches_by_match(db, match_id, user_id=target_user_id)

