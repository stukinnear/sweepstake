"""Team management routes: create, read, update, delete operations."""

from fastapi import APIRouter, BackgroundTasks, Depends, status, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.exceptions import CustomError
from src.teams import crud, models
from src.tournaments.crud import is_admin as is_tournament_admin
from src.users.routers import verify_access_token

router = APIRouter(prefix="/team", tags=["team"])


@router.post("", response_model=models.TeamRead, status_code=status.HTTP_201_CREATED)
async def create_team_endpoint(
    team: models.TeamCreate,
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Depends(verify_access_token),
):
    """
    Create a new team (tournament admins only).

    - **tournament_id**: ID of the tournament this team belongs to
    - **name**: Team name (required)
    - **iso_code**: ISO country/team code (e.g. "DE", "FR")
    - **image_url**: URL to the team's flag or logo
    - **football_data_org_id**: Optional football-data.org team ID
    - **group_id**: Optional ID of the group this team belongs to

    Returns the created team.
    """
    if not await is_tournament_admin(db, team.tournament_id, token_payload["uid"]):
        raise CustomError("Forbidden: only tournament admins can create teams", status_code=403)
    return await crud.create_team(db, team)


@router.get("", response_model=list[models.TeamRead])
async def get_teams_endpoint(
    tournament_id: int = Query(..., description="Filter teams by tournament ID", gt=0),
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Depends(verify_access_token),
):
    """
    Retrieve all teams for a tournament.

    - **tournament_id**: The tournament to retrieve teams for (required)

    Returns a list of teams ordered alphabetically.
    Only accessible to participants and admins of the tournament.
    """
    if not await crud.is_participant_or_admin(db, tournament_id, token_payload["uid"]):
        raise CustomError("Forbidden: only participants and admins can view teams", status_code=403)
    return await crud.get_teams_by_tournament(db, tournament_id)


@router.get("/{team_id}", response_model=models.TeamRead)
async def get_team_endpoint(
    team_id: int = Path(..., description="Unique team identifier", gt=0),
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Depends(verify_access_token),
):
    """
    Retrieve a specific team by ID.

    - **team_id**: The unique identifier of the team

    Returns the team details or 404 if not found.
    Only accessible to participants and admins of the team's tournament.
    """
    team = await crud.get_team_by_id(db, team_id)
    if not team:
        raise CustomError("Team not found", status_code=404)
    if not await crud.is_participant_or_admin(db, team.tournament_id, token_payload["uid"]):
        raise CustomError("Forbidden: only participants and admins can view teams", status_code=403)
    return team


@router.patch("/{team_id}", response_model=models.TeamRead)
async def patch_team_endpoint(
    background_tasks: BackgroundTasks,
    team_id: int = Path(..., description="Unique team identifier", gt=0),
    team: models.TeamUpdate = None,
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Depends(verify_access_token),
):
    """
    Update an existing team (tournament admins only).

    - **team_id**: The unique identifier of the team to update
    - **name**: Team name
    - **iso_code**: ISO country/team code (e.g. "DE", "FR")
    - **image_url**: URL to the team's flag or logo
    - **football_data_org_id**: Optional football-data.org team ID
    - **group_id**: Optional ID of the group this team belongs to

    Returns the updated team or 404 if not found.
    """
    existing = await crud.get_team_by_id(db, team_id)
    if not existing:
        raise CustomError("Team not found", status_code=404)
    if not await is_tournament_admin(db, existing.tournament_id, token_payload["uid"]):
        raise CustomError("Forbidden: only tournament admins can modify teams", status_code=403)
    return await crud.update_team(db, team_id, team, background_tasks)


@router.delete("/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_team_endpoint(
    team_id: int = Path(..., description="Unique team identifier", gt=0),
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Depends(verify_access_token),
):
    """
    Delete a team (tournament admins only).

    - **team_id**: The unique identifier of the team to delete

    Returns 204 No Content on success or 404 if not found.
    """
    existing = await crud.get_team_by_id(db, team_id)
    if not existing:
        raise CustomError("Team not found", status_code=404)
    if not await is_tournament_admin(db, existing.tournament_id, token_payload["uid"]):
        raise CustomError("Forbidden: only tournament admins can delete teams", status_code=403)
    await crud.delete_team(db, team_id)
    return None
