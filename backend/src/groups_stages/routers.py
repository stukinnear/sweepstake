"""Group and Stage management routes: create, read, update, delete operations."""

from fastapi import APIRouter, BackgroundTasks, Depends, status, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.exceptions import CustomError
from src.groups_stages import crud, models
from src.tournaments.crud import is_admin as is_tournament_admin
from src.users.routers import verify_access_token

group_router = APIRouter(prefix="/group", tags=["group"])
stage_router = APIRouter(prefix="/stage", tags=["stage"])


# ===========================================================================
# Group routes
# ===========================================================================

@group_router.post("", response_model=models.GroupRead, status_code=status.HTTP_201_CREATED)
async def create_group_endpoint(
    group: models.GroupCreate,
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Depends(verify_access_token),
):
    """
    Create a new group (tournament admins only).

    - **tournament_id**: ID of the tournament this group belongs to
    - **name**: Group name (required)
    - **winner_team_id**: Optional team ID of the group winner

    Returns the created group.
    """
    if not await is_tournament_admin(db, group.tournament_id, token_payload["uid"]):
        raise CustomError("Forbidden: only tournament admins can create groups", status_code=403)
    return await crud.create_group(db, group)


@group_router.get("", response_model=list[models.GroupRead])
async def get_groups_endpoint(
    tournament_id: int = Query(..., description="Filter groups by tournament ID", gt=0),
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Depends(verify_access_token),
):
    """
    Retrieve all groups for a tournament.

    - **tournament_id**: The tournament to retrieve groups for (required)

    Returns a list of groups ordered alphabetically.
    Only accessible to participants and admins of the tournament.
    """
    if not await crud.is_participant_or_admin(db, tournament_id, token_payload["uid"]):
        raise CustomError("Forbidden: only participants and admins can view groups", status_code=403)
    return await crud.get_groups_by_tournament(db, tournament_id)


@group_router.get("/{group_id}", response_model=models.GroupRead)
async def get_group_endpoint(
    group_id: int = Path(..., description="Unique group identifier", gt=0),
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Depends(verify_access_token),
):
    """
    Retrieve a specific group by ID.

    - **group_id**: The unique identifier of the group

    Returns the group details or 404 if not found.
    Only accessible to participants and admins of the group's tournament.
    """
    group = await crud.get_group_by_id(db, group_id)
    if not group:
        raise CustomError("Group not found", status_code=404)
    if not await crud.is_participant_or_admin(db, group.tournament_id, token_payload["uid"]):
        raise CustomError("Forbidden: only participants and admins can view groups", status_code=403)
    return group


@group_router.patch("/{group_id}", response_model=models.GroupRead)
async def patch_group_endpoint(
    background_tasks: BackgroundTasks,
    group_id: int = Path(..., description="Unique group identifier", gt=0),
    group: models.GroupUpdate = None,
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Depends(verify_access_token),
):
    """
    Update an existing group (tournament admins only).

    - **group_id**: The unique identifier of the group to update
    - **name**: Group name
    - **winner_team_id**: Optional team ID of the group winner

    Returns the updated group or 404 if not found.
    """
    existing = await crud.get_group_by_id(db, group_id)
    if not existing:
        raise CustomError("Group not found", status_code=404)
    if not await is_tournament_admin(db, existing.tournament_id, token_payload["uid"]):
        raise CustomError("Forbidden: only tournament admins can modify groups", status_code=403)
    return await crud.update_group(db, group_id, group, background_tasks)


@group_router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_group_endpoint(
    group_id: int = Path(..., description="Unique group identifier", gt=0),
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Depends(verify_access_token),
):
    """
    Delete a group (tournament admins only).

    - **group_id**: The unique identifier of the group to delete

    Returns 204 No Content on success or 404 if not found.
    """
    existing = await crud.get_group_by_id(db, group_id)
    if not existing:
        raise CustomError("Group not found", status_code=404)
    if not await is_tournament_admin(db, existing.tournament_id, token_payload["uid"]):
        raise CustomError("Forbidden: only tournament admins can delete groups", status_code=403)
    await crud.delete_group(db, group_id)
    return None


# ===========================================================================
# Stage routes
# ===========================================================================

@stage_router.post("", response_model=models.StageRead, status_code=status.HTTP_201_CREATED)
async def create_stage_endpoint(
    stage: models.StageCreate,
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Depends(verify_access_token),
):
    """
    Create a new stage (tournament admins only).

    - **tournament_id**: ID of the tournament this stage belongs to
    - **name**: Stage name (required, e.g. "Group Stage", "Quarter-finals")
    - **winner_team_id**: Optional team ID of the stage winner

    Returns the created stage.
    """
    if not await is_tournament_admin(db, stage.tournament_id, token_payload["uid"]):
        raise CustomError("Forbidden: only tournament admins can create stages", status_code=403)
    return await crud.create_stage(db, stage)


@stage_router.get("", response_model=list[models.StageRead])
async def get_stages_endpoint(
    tournament_id: int = Query(..., description="Filter stages by tournament ID", gt=0),
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Depends(verify_access_token),
):
    """
    Retrieve all stages for a tournament.

    - **tournament_id**: The tournament to retrieve stages for (required)

    Returns a list of stages ordered alphabetically.
    Only accessible to participants and admins of the tournament.
    """
    if not await crud.is_participant_or_admin(db, tournament_id, token_payload["uid"]):
        raise CustomError("Forbidden: only participants and admins can view stages", status_code=403)
    return await crud.get_stages_by_tournament(db, tournament_id)


@stage_router.get("/{stage_id}", response_model=models.StageRead)
async def get_stage_endpoint(
    stage_id: int = Path(..., description="Unique stage identifier", gt=0),
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Depends(verify_access_token),
):
    """
    Retrieve a specific stage by ID.

    - **stage_id**: The unique identifier of the stage

    Returns the stage details or 404 if not found.
    Only accessible to participants and admins of the stage's tournament.
    """
    stage = await crud.get_stage_by_id(db, stage_id)
    if not stage:
        raise CustomError("Stage not found", status_code=404)
    if not await crud.is_participant_or_admin(db, stage.tournament_id, token_payload["uid"]):
        raise CustomError("Forbidden: only participants and admins can view stages", status_code=403)
    return stage


@stage_router.patch("/{stage_id}", response_model=models.StageRead)
async def patch_stage_endpoint(
    background_tasks: BackgroundTasks,
    stage_id: int = Path(..., description="Unique stage identifier", gt=0),
    stage: models.StageUpdate = None,
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Depends(verify_access_token),
):
    """
    Update an existing stage (tournament admins only).

    - **stage_id**: The unique identifier of the stage to update
    - **name**: Stage name
    - **winner_team_id**: Optional team ID of the stage winner

    Returns the updated stage or 404 if not found.
    """
    existing = await crud.get_stage_by_id(db, stage_id)
    if not existing:
        raise CustomError("Stage not found", status_code=404)
    if not await is_tournament_admin(db, existing.tournament_id, token_payload["uid"]):
        raise CustomError("Forbidden: only tournament admins can modify stages", status_code=403)
    return await crud.update_stage(db, stage_id, stage, background_tasks)


@stage_router.delete("/{stage_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_stage_endpoint(
    stage_id: int = Path(..., description="Unique stage identifier", gt=0),
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Depends(verify_access_token),
):
    """
    Delete a stage (tournament admins only).

    - **stage_id**: The unique identifier of the stage to delete

    Returns 204 No Content on success or 404 if not found.
    """
    existing = await crud.get_stage_by_id(db, stage_id)
    if not existing:
        raise CustomError("Stage not found", status_code=404)
    if not await is_tournament_admin(db, existing.tournament_id, token_payload["uid"]):
        raise CustomError("Forbidden: only tournament admins can delete stages", status_code=403)
    await crud.delete_stage(db, stage_id)
    return None
