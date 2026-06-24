from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ProviderCompetition(BaseModel):
    id: str
    name: str
    area: Optional[str] = None
    current_season_start: Optional[str] = None
    current_season_end: Optional[str] = None
    emblem_url: Optional[str] = None
    provider: str


class ProviderDiagnostics(BaseModel):
    tournament_id: int
    provider: Optional[str] = None
    configured_provider: str
    competition_format: Optional[str] = None
    competition_id: Optional[str] = None
    configured_league_id: Optional[str] = None
    season: Optional[str] = None
    team_count: int
    match_count: int
    last_update_status: Optional[str] = None
    last_update_message: Optional[str] = None
    last_updated_at: Optional[datetime] = None
    last_update_match_count: Optional[int] = None
    last_update_team_count: Optional[int] = None
    warnings: list[str] = Field(default_factory=list)


class ProviderTeam(BaseModel):
    external_id: Optional[str]
    name: str
    iso_code: Optional[str] = None
    image_url: Optional[str] = None


class ProviderMatch(BaseModel):
    external_id: str
    start_datetime: datetime
    status: str
    home_team: Optional[ProviderTeam] = None
    away_team: Optional[ProviderTeam] = None
    home_goals: Optional[int] = None
    away_goals: Optional[int] = None
    group_name: Optional[str] = None
    stage_name: Optional[str] = None
