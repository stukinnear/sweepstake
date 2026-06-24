from fastapi import APIRouter, Depends, Path, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.database import get_db
from src.exceptions import CustomError
from src.matches.models import Match
from src.providers import get_provider
from src.providers.models import ProviderDiagnostics
from src.teams.models import Team
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


@router.get("/diagnostics/{tournament_id}", response_model=ProviderDiagnostics)
async def get_provider_diagnostics(
    tournament_id: int = Path(..., description="Tournament ID to inspect"),
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Depends(verify_access_token),
):
    """
    Return provider import diagnostics for a tournament.

    Only tournament admins can view this. The response is based on stored
    tournament, team, and match data so it is safe to open without calling the
    upstream provider API.
    """
    tournament = await db.get(tournament_models.Tournament, tournament_id)
    if not tournament:
        raise CustomError("Tournament not found", status_code=404)
    user_id = token_payload["uid"]
    if not await tournament_crud.is_admin(db, tournament_id, user_id):
        raise CustomError("Forbidden: only admins can view provider diagnostics", status_code=403)

    team_count = (
        await db.execute(
            select(func.count()).select_from(Team).where(Team.tournament_id == tournament_id)
        )
    ).scalar_one()
    match_count = (
        await db.execute(
            select(func.count()).select_from(Match).where(Match.tournament_id == tournament_id)
        )
    ).scalar_one()

    provider_id = tournament.external_provider or ("football-data-org" if tournament.football_data_org_id else None)
    competition_id = tournament.external_id or (str(tournament.football_data_org_id) if tournament.football_data_org_id else None)
    configured_league_id = settings.thesportsdb_league_id if provider_id == "thesportsdb" else None
    season = settings.thesportsdb_season if provider_id == "thesportsdb" else None
    warnings: list[str] = []

    if not provider_id or not competition_id:
        warnings.append("This tournament is not linked to an external provider.")
    if provider_id and provider_id != settings.football_provider:
        warnings.append(f"Configured provider is {settings.football_provider}, but this tournament uses {provider_id}.")
    if provider_id == "thesportsdb" and competition_id != settings.thesportsdb_league_id:
        warnings.append(f"TheSportsDB league ID is configured as {settings.thesportsdb_league_id}, but this tournament uses {competition_id}.")
    if provider_id == "thesportsdb" and team_count != 12:
        warnings.append(f"Scottish Premiership should have 12 teams; this tournament has {team_count}.")
    if team_count == 0:
        warnings.append("No teams have been imported for this tournament.")
    if match_count == 0:
        warnings.append("No matches have been imported for this tournament.")
    if tournament.provider_update_status == "failed":
        warnings.append(tournament.provider_update_message or "The last provider update failed.")

    return ProviderDiagnostics(
        tournament_id=tournament_id,
        provider=provider_id,
        configured_provider=settings.football_provider,
        competition_format=tournament_models.infer_competition_format(
            tournament.external_provider,
            tournament.competition_format,
        ),
        competition_id=competition_id,
        configured_league_id=configured_league_id,
        season=season,
        team_count=team_count,
        match_count=match_count,
        last_update_status=tournament.provider_update_status,
        last_update_message=tournament.provider_update_message,
        last_updated_at=tournament.provider_updated_at,
        last_update_match_count=tournament.provider_update_match_count,
        last_update_team_count=tournament.provider_update_team_count,
        warnings=warnings,
    )


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
