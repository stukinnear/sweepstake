from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ProviderCompetition(BaseModel):
    id: str
    name: str
    area: Optional[str] = None
    current_season_start: Optional[str] = None
    current_season_end: Optional[str] = None
    emblem_url: Optional[str] = None
    provider: str


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
