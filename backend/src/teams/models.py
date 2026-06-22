from typing import TYPE_CHECKING, List, Optional

import sqlalchemy as sa
from pydantic import ConfigDict, model_validator
from sqlmodel import SQLModel, Field, Relationship

from src.groups_stages.models import GroupRead, StageRead
from src.utils import all_optional

if TYPE_CHECKING:
    from src.groups_stages.models import Group
    from src.matches.models import Match


# ---------------------------------------------------------------------------
# Base / DB model
# ---------------------------------------------------------------------------

class TeamBase(SQLModel):
    """Shared team fields used across create, read, and update schemas."""
    name: str = Field(..., min_length=1, max_length=255)
    iso_code: Optional[str] = Field(default=None, max_length=10)
    image_url: Optional[str] = Field(default=None, max_length=512)
    external_provider: Optional[str] = Field(default=None, max_length=64)
    external_id: Optional[str] = Field(default=None, max_length=128)
    football_data_org_id: Optional[int] = Field(default=None)
    group_id: Optional[int] = Field(default=None)


class Team(TeamBase, table=True):
    __tablename__ = "team"

    id: Optional[int] = Field(default=None, primary_key=True)
    tournament_id: Optional[int] = Field(
        default=None,
        sa_column=sa.Column(sa.Integer, sa.ForeignKey("tournament.id", ondelete="CASCADE"), nullable=True, index=True)
    )
    group_id: Optional[int] = Field(
        default=None,
        sa_column=sa.Column(sa.Integer, sa.ForeignKey("tournament_group.id", ondelete="SET NULL"), nullable=True, index=True)
    )
    external_provider: Optional[str] = Field(default=None, sa_column=sa.Column(sa.String(64), nullable=True, index=True))
    external_id: Optional[str] = Field(default=None, sa_column=sa.Column(sa.String(128), nullable=True, index=True))
    # Legacy column retained so existing installs do not drop provider IDs during startup auto-migration.
    football_data_org_id: Optional[int] = Field(default=None)

    group: Optional["Group"] = Relationship(  # type: ignore[name-defined]
        sa_relationship_kwargs={
            "primaryjoin": "Team.group_id == Group.id",
            "foreign_keys": "[Team.group_id]",
            "lazy": "selectin",
            "overlaps": "teams",
        }
    )
    home_matches: List["Match"] = Relationship(
        sa_relationship_kwargs={
            "primaryjoin": "Team.id == Match.home_team_id",
            "foreign_keys": "[Match.home_team_id]",
            "lazy": "selectin",
        }
    )
    away_matches: List["Match"] = Relationship(
        sa_relationship_kwargs={
            "primaryjoin": "Team.id == Match.away_team_id",
            "foreign_keys": "[Match.away_team_id]",
            "lazy": "selectin",
        }
    )


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------

class TeamCreate(TeamBase):
    """Body for POST /team."""
    tournament_id: int


@all_optional
class TeamUpdate(TeamBase):
    """Body for PATCH /team/{id} — all fields optional."""


class TeamRead(TeamBase):
    """Response model returned by all team endpoints."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    tournament_id: int
    group_name: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def _populate_group_name(cls, data):
        if isinstance(data, dict):
            return data
        group = getattr(data, "group", None)
        if group is not None:
            return {
                "id": data.id,
                "name": data.name,
                "iso_code": data.iso_code,
                "image_url": data.image_url,
                "external_provider": data.external_provider,
                "external_id": data.external_id,
                "football_data_org_id": data.football_data_org_id,
                "group_id": data.group_id,
                "tournament_id": data.tournament_id,
                "group_name": group.name,
            }
        return data


# Resolve forward references in groups_stages models now that TeamRead is defined
GroupRead.model_rebuild(_types_namespace={"TeamRead": TeamRead})
StageRead.model_rebuild(_types_namespace={"TeamRead": TeamRead})
