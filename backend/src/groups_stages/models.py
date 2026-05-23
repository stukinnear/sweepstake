from datetime import date
from typing import TYPE_CHECKING, List, Optional

import sqlalchemy as sa
from pydantic import ConfigDict, model_validator
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from src.teams.models import Team, TeamRead
    from src.matches.models import Match

from src.utils import all_optional


# ---------------------------------------------------------------------------
# Group
# ---------------------------------------------------------------------------

class GroupBase(SQLModel):
    """Shared group fields used across create, read, and update schemas."""
    name: str = Field(..., min_length=1, max_length=255)
    winner_team_id: Optional[int] = Field(default=None)
    winner_points: Optional[int] = Field(default=None)


class Group(GroupBase, table=True):
    __tablename__ = "tournament_group"

    id: Optional[int] = Field(default=None, primary_key=True)
    tournament_id: Optional[int] = Field(
        default=None,
        sa_column=sa.Column(sa.Integer, sa.ForeignKey("tournament.id", ondelete="CASCADE"), nullable=True, index=True)
    )
    winner_team_id: Optional[int] = Field(
        default=None,
        sa_column=sa.Column(
            sa.Integer,
            sa.ForeignKey("team.id", ondelete="SET NULL", use_alter=True, name="fk_group_winner_team_id"),
            nullable=True,
        ),
    )

    winner: Optional["Team"] = Relationship(
        sa_relationship_kwargs={
            "primaryjoin": "Group.winner_team_id == Team.id",
            "foreign_keys": "[Group.winner_team_id]",
            "lazy": "selectin",
        }
    )
    teams: List["Team"] = Relationship(
        sa_relationship_kwargs={
            "primaryjoin": "Group.id == Team.group_id",
            "foreign_keys": "[Team.group_id]",
            "lazy": "selectin",
        }
    )


class GroupCreate(GroupBase):
    """Body for POST /group."""
    tournament_id: int


@all_optional
class GroupUpdate(GroupBase):
    """Body for PATCH /group/{id} — all fields optional."""


class GroupRead(GroupBase):
    """Response model returned by all group endpoints."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    tournament_id: int
    winner: Optional["TeamRead"] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None

    @model_validator(mode="before")
    @classmethod
    def populate_dates(cls, data):
        d = getattr(data, "__dict__", {})
        if "teams" not in d:
            return data  # teams relationship not loaded — skip date computation
        match_dates = []
        for team in d["teams"]:
            td = getattr(team, "__dict__", {})
            for match in td.get("home_matches", []):
                if match.start_datetime is not None:
                    match_dates.append(match.start_datetime.date())
            for match in td.get("away_matches", []):
                if match.start_datetime is not None:
                    match_dates.append(match.start_datetime.date())
        data.__dict__.setdefault("start_date", min(match_dates) if match_dates else None)
        data.__dict__.setdefault("end_date", max(match_dates) if match_dates else None)
        return data


# ---------------------------------------------------------------------------
# Stage
# ---------------------------------------------------------------------------

class StageBase(SQLModel):
    """Shared stage fields used across create, read, and update schemas."""
    name: str = Field(..., min_length=1, max_length=255)
    winner_team_id: Optional[int] = Field(default=None)
    winner_points: Optional[int] = Field(default=None)


class Stage(StageBase, table=True):
    __tablename__ = "stage"

    id: Optional[int] = Field(default=None, primary_key=True)
    tournament_id: Optional[int] = Field(
        default=None,
        sa_column=sa.Column(sa.Integer, sa.ForeignKey("tournament.id", ondelete="CASCADE"), nullable=True, index=True)
    )
    winner_team_id: Optional[int] = Field(
        default=None,
        sa_column=sa.Column(
            sa.Integer,
            sa.ForeignKey("team.id", ondelete="SET NULL", use_alter=True, name="fk_stage_winner_team_id"),
            nullable=True,
        ),
    )

    winner: Optional["Team"] = Relationship(
        sa_relationship_kwargs={
            "primaryjoin": "Stage.winner_team_id == Team.id",
            "foreign_keys": "[Stage.winner_team_id]",
            "lazy": "selectin",
        }
    )
    matches: List["Match"] = Relationship(  # noqa: F821
        sa_relationship_kwargs={
            "primaryjoin": "Stage.id == Match.stage_id",
            "foreign_keys": "[Match.stage_id]",
            "lazy": "selectin",
        }
    )


class StageCreate(StageBase):
    """Body for POST /stage."""
    tournament_id: int


@all_optional
class StageUpdate(StageBase):
    """Body for PATCH /stage/{id} — all fields optional."""


class StageRead(StageBase):
    """Response model returned by all stage endpoints."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    tournament_id: int
    winner: Optional["TeamRead"] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None

    @model_validator(mode="before")
    @classmethod
    def populate_dates(cls, data):
        d = getattr(data, "__dict__", {})
        if "matches" not in d:
            return data  # matches relationship not loaded — skip date computation
        match_dates = [m.start_datetime.date() for m in d["matches"] if m.start_datetime is not None]
        data.__dict__.setdefault("start_date", min(match_dates) if match_dates else None)
        data.__dict__.setdefault("end_date", max(match_dates) if match_dates else None)
        return data
