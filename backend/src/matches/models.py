from datetime import datetime
from typing import Optional

import sqlalchemy as sa
from pydantic import ConfigDict, computed_field
from sqlalchemy import DateTime
from sqlmodel import SQLModel, Field, Relationship, Column

from src.teams.models import Team, TeamRead
from src.groups_stages.models import Stage, StageRead
from src.utils import all_optional


# ---------------------------------------------------------------------------
# Base / DB model
# ---------------------------------------------------------------------------

class MatchBase(SQLModel):
    """Shared match fields used across create, read, and update schemas."""
    start_datetime: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    home_goals: Optional[int] = Field(default=None, ge=0)
    away_goals: Optional[int] = Field(default=None, ge=0)
    football_data_org_id: Optional[int] = Field(default=None)
    tv_channel: Optional[str] = Field(default=None)


class Match(MatchBase, table=True):
    __tablename__ = "match"

    id: Optional[int] = Field(default=None, primary_key=True)
    tournament_id: Optional[int] = Field(
        default=None,
        sa_column=sa.Column(sa.Integer, sa.ForeignKey("tournament.id", ondelete="CASCADE"), nullable=True, index=True)
    )
    home_team_id: Optional[int] = Field(
        default=None,
        sa_column=sa.Column(sa.Integer, sa.ForeignKey("team.id", ondelete="SET NULL"), nullable=True)
    )
    away_team_id: Optional[int] = Field(
        default=None,
        sa_column=sa.Column(sa.Integer, sa.ForeignKey("team.id", ondelete="SET NULL"), nullable=True)
    )
    stage_id: Optional[int] = Field(
        default=None,
        sa_column=sa.Column(sa.Integer, sa.ForeignKey("stage.id", ondelete="SET NULL"), nullable=True, index=True)
    )

    home_team: Optional[Team] = Relationship(
        sa_relationship_kwargs={
            "primaryjoin": "Match.home_team_id == Team.id",
            "foreign_keys": "[Match.home_team_id]",
            "lazy": "selectin",
            "overlaps": "home_matches",
        }
    )
    away_team: Optional[Team] = Relationship(
        sa_relationship_kwargs={
            "primaryjoin": "Match.away_team_id == Team.id",
            "foreign_keys": "[Match.away_team_id]",
            "lazy": "selectin",
            "overlaps": "away_matches",
        }
    )
    stage: Optional[Stage] = Relationship(
        sa_relationship_kwargs={
            "primaryjoin": "Match.stage_id == Stage.id",
            "foreign_keys": "[Match.stage_id]",
            "lazy": "selectin",
            "overlaps": "matches",
        }
    )


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------

class MatchCreate(MatchBase):
    """Body for POST /match."""
    tournament_id: int
    home_team_id: Optional[int] = None
    away_team_id: Optional[int] = None
    stage_id: Optional[int] = None


@all_optional
class MatchUpdate(MatchBase):
    """Body for PATCH /match/{id} — all fields optional."""
    home_team_id: Optional[int] = None
    away_team_id: Optional[int] = None
    stage_id: Optional[int] = None


class MatchRead(MatchBase):
    """Response model returned by all match endpoints."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    tournament_id: int
    home_team_id: Optional[int] = None
    away_team_id: Optional[int] = None
    stage_id: Optional[int] = None
    home_team: Optional[TeamRead] = None
    away_team: Optional[TeamRead] = None
    stage: Optional[StageRead] = Field(default=None, exclude=True)

    @computed_field
    @property
    def stage_name(self) -> Optional[str]:
        return self.stage.name if self.stage else None
