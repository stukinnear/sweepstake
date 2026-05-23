"""Match management routes: create, read, update, delete operations."""

from fastapi import APIRouter, BackgroundTasks, Depends, status, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.exceptions import CustomError
from src.matches import crud, models
from src.tournaments.crud import is_admin as is_tournament_admin
from src.users.routers import verify_access_token

router = APIRouter(prefix="/match", tags=["match"])


@router.post("", response_model=models.MatchRead, status_code=status.HTTP_201_CREATED)
async def create_match_endpoint(
    match: models.MatchCreate,
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Depends(verify_access_token),
):
    """
    Create a new match (tournament admins only).

    - **tournament_id**: ID of the tournament this match belongs to
    - **start_datetime**: Match start date and time in ISO format (YYYY-MM-DDTHH:MM:SS)
    - **home_team_id**: ID of the home team
    - **away_team_id**: ID of the away team
    - **stage_id**: Optional ID of the stage this match belongs to
    - **home_goals**: Home team goals (optional, set after match)
    - **away_goals**: Away team goals (optional, set after match)
    - **football_data_org_id**: Optional football-data.org match ID

    Returns the created match with nested team details.
    """
    if not await is_tournament_admin(db, match.tournament_id, token_payload["uid"]):
        raise CustomError("Forbidden: only tournament admins can create matches", status_code=403)
    return await crud.create_match(db, match)


@router.get("", response_model=list[models.MatchRead])
async def get_matches_endpoint(
    tournament_id: int = Query(..., description="Filter matches by tournament ID", gt=0),
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Depends(verify_access_token),
):
    """
    Retrieve all matches for a tournament.

    - **tournament_id**: The tournament to retrieve matches for (required)

    Returns a list of matches ordered by start time, with nested team details.
    Only accessible to participants and admins of the tournament.
    """
    user_id = token_payload["uid"]
    if not await crud.is_participant_or_admin(db, tournament_id, user_id):
        raise CustomError("Forbidden: only participants and admins can view matches", status_code=403)
    return await crud.get_matches_by_tournament(db, tournament_id)


@router.get("/{match_id}", response_model=models.MatchRead)
async def get_match_endpoint(
    match_id: int = Path(..., description="Unique match identifier", gt=0),
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Depends(verify_access_token),
):
    """
    Retrieve a specific match by ID.

    - **match_id**: The unique identifier of the match

    Returns the match details with nested team data, or 404 if not found.
    Only accessible to participants and admins of the match's tournament.
    """
    match = await crud.get_match_by_id(db, match_id)
    if not match:
        raise CustomError("Match not found", status_code=404)
    if not await crud.is_participant_or_admin(db, match.tournament_id, token_payload["uid"]):
        raise CustomError("Forbidden: only participants and admins can view matches", status_code=403)
    return match


@router.patch("/{match_id}", response_model=models.MatchRead)
async def patch_match_endpoint(
    background_tasks: BackgroundTasks,
    match_id: int = Path(..., description="Unique match identifier", gt=0),
    match: models.MatchUpdate = None,
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Depends(verify_access_token),
):
    """
    Update an existing match (tournament admins only).

    - **match_id**: The unique identifier of the match to update
    - **start_datetime**: Match start date and time in ISO format (YYYY-MM-DDTHH:MM:SS)
    - **home_team_id**: ID of the home team
    - **away_team_id**: ID of the away team
    - **stage_id**: Optional ID of the stage this match belongs to
    - **home_goals**: Home team goals
    - **away_goals**: Away team goals
    - **football_data_org_id**: Optional football-data.org match ID

    Returns the updated match or 404 if not found.
    """
    existing = await crud.get_match_by_id(db, match_id)
    if not existing:
        raise CustomError("Match not found", status_code=404)
    if not await is_tournament_admin(db, existing.tournament_id, token_payload["uid"]):
        raise CustomError("Forbidden: only tournament admins can modify matches", status_code=403)
    return await crud.update_match(db, match_id, match, background_tasks)


@router.delete("/{match_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_match_endpoint(
    match_id: int = Path(..., description="Unique match identifier", gt=0),
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Depends(verify_access_token),
):
    """
    Delete a match (tournament admins only).

    - **match_id**: The unique identifier of the match to delete

    Returns 204 No Content on success or 404 if not found.
    """
    existing = await crud.get_match_by_id(db, match_id)
    if not existing:
        raise CustomError("Match not found", status_code=404)
    if not await is_tournament_admin(db, existing.tournament_id, token_payload["uid"]):
        raise CustomError("Forbidden: only tournament admins can delete matches", status_code=403)
    await crud.delete_match(db, match_id)
    return None
