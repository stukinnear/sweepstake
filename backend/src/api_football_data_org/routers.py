"""Routes for football-data.org integration."""

from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.tournaments import crud as tournament_crud, models as tournament_models
from src.users.routers import verify_access_token
from src.api_football_data_org.list_tournaments import list_tournaments

router = APIRouter(prefix="/football-data-org", tags=["football-data-org"])


@router.get("/tournaments")
async def list_football_data_org_tournaments(
    token_payload: dict = Depends(verify_access_token),
):
    """
    List available tournaments from football-data.org.

    Returns all TIER_ONE competitions that have a current or future season,
    formatted with name, area, season dates, and emblem URL.
    """
    return await list_tournaments()


@router.post("/import/{competition_id}", response_model=tournament_models.TournamentRead, status_code=status.HTTP_201_CREATED)
async def import_football_data_org_tournament(
    tournament: tournament_models.TournamentCreate | None = None,
    competition_id: int = Path(..., description="football-data.org competition ID", gt=0),
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Depends(verify_access_token),
):
    """
    Import a football-data.org competition into a new tournament.

    Prefer `POST /providers/import/football-data-org/{competition_id}` for new integrations.
    """
    if tournament is None:
        tournament = tournament_models.TournamentCreate(
            name=f"football-data.org {competition_id}",
            external_provider="football-data-org",
            external_id=str(competition_id),
        )
    else:
        tournament.external_provider = "football-data-org"
        tournament.external_id = str(competition_id)
    return await tournament_crud.create_tournament(db, tournament, user_id=token_payload["uid"])
