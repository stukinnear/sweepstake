from src.config import settings
from src.providers.base import FootballProvider
from src.providers.football_data_org import FootballDataOrgProvider
from src.providers.thesportsdb import TheSportsDBProvider


def get_provider(provider_id: str | None = None) -> FootballProvider:
    selected = provider_id or settings.football_provider
    providers: dict[str, FootballProvider] = {
        "football-data-org": FootballDataOrgProvider(),
        "thesportsdb": TheSportsDBProvider(),
    }
    if selected not in providers:
        raise ValueError(f"Unsupported football provider: {selected}")
    return providers[selected]
