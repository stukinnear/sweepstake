async def list_tournaments() -> list:
    from src.providers import get_provider

    competitions = await get_provider("football-data-org").list_competitions()
    return [competition.model_dump(exclude={"provider"}) for competition in competitions]
