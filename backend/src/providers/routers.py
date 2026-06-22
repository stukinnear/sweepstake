from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.exceptions import CustomError
from src.providers import get_provider
from src.tournaments import crud as tournament_crud, models as tournament_models
from src.users.routers import verify_access_token

router = APIRouter(prefix="/providers", tags=["providers"])


@router.get("/tournaments")
async def list_provider_tournaments(
    token_payload: dict = Depends(verify_access_token),
):
    """
    List available tournaments from the configured football data provider.

    Set `FOOTBALL_PROVIDER` to `football-data-org` or `thesportsdb`.
    """
    return await get_provider().list_competitions()


@router.post("/import/{provider}/{competition_id}", response_model=tournament_models.TournamentRead, status_code=status.HTTP_201_CREATED)
async def import_provider_competition(
    tournament: tournament_models.TournamentCreate | None = None,
    provider: str = Path(..., description="Provider ID: football-data-org or thesportsdb"),
    competition_id: str = Path(..., description="Provider competition/league ID"),
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Depends(verify_access_token),
):
    """
    Import a provider competition into a new tournament.

    If no body is sent, the tournament name is taken from the provider's
    competition list. A supplied body can override name, stake, and scoring.
    """
    try:
        selected_provider = get_provider(provider)
    except ValueError as exc:
        raise CustomError(str(exc), status_code=400) from exc

    if tournament is None:
        competitions = await selected_provider.list_competitions()
        competition = next((item for item in competitions if item.id == str(competition_id)), None)
        name = competition.name if competition else f"{provider} {competition_id}"
        tournament = tournament_models.TournamentCreate(
            name=name,
            external_provider=provider,
            external_id=str(competition_id),
        )
    else:
        tournament.external_provider = provider
        tournament.external_id = str(competition_id)

    return await tournament_crud.create_tournament(db, tournament, user_id=token_payload["uid"])
