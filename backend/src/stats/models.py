"""Response schemas for stats endpoints. No database tables."""

from datetime import datetime
from typing import List, Optional

from pydantic import ConfigDict
from sqlmodel import SQLModel

from src.teams.models import TeamRead


class LeaderboardEntry(SQLModel):
    model_config = ConfigDict(from_attributes=True)

    rank: int
    user_id: int
    user_name: Optional[str] = None
    total_points: int


class UserPredictionMatch(SQLModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    user_name: Optional[str] = None
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    points_earned: Optional[int] = None


class MatchStatsRead(SQLModel):
    model_config = ConfigDict(from_attributes=True)

    match_id: int
    start_datetime: Optional[datetime] = None
    home_goals: Optional[int] = None
    away_goals: Optional[int] = None
    predictions: List[UserPredictionMatch]


class WinnerPredictionUser(SQLModel):
    """A single user's entry within a grouped winner-prediction response."""
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    user_name: Optional[str] = None
    points_earned: Optional[int] = None


class WinnerPredictionGroup(SQLModel):
    """Flattened TeamRead fields plus all users who picked that team.

    All team fields are Optional to accommodate the no-prediction bucket
    (users who submitted no prediction).
    """
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    name: Optional[str] = None
    iso_code: Optional[str] = None
    image_url: Optional[str] = None
    football_data_org_id: Optional[int] = None
    group_id: Optional[int] = None
    tournament_id: Optional[int] = None
    group_name: Optional[str] = None
    users: List[WinnerPredictionUser]


class GroupStatsRead(SQLModel):
    model_config = ConfigDict(from_attributes=True)

    group_id: int
    actual_winner_team_id: Optional[int] = None
    actual_winner_team: Optional[TeamRead] = None
    predictions: List[WinnerPredictionGroup]


class StageStatsRead(SQLModel):
    model_config = ConfigDict(from_attributes=True)

    stage_id: int
    actual_winner_team_id: Optional[int] = None
    actual_winner_team: Optional[TeamRead] = None
    predictions: List[WinnerPredictionGroup]


class TournamentStatsRead(SQLModel):
    model_config = ConfigDict(from_attributes=True)

    tournament_id: int
    first_place_team_id: Optional[int] = None
    first_place_team: Optional[TeamRead] = None
    second_place_team_id: Optional[int] = None
    second_place_team: Optional[TeamRead] = None
    third_place_team_id: Optional[int] = None
    third_place_team: Optional[TeamRead] = None
    predictions: List[WinnerPredictionGroup]


class ParticipantActivityEntry(SQLModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    user_name: Optional[str] = None
    tournament_predictions: int
    group_predictions: int
    stage_predictions: int
    match_predictions: int
