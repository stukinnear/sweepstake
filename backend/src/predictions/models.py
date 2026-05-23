from typing import Optional

import sqlalchemy as sa
from pydantic import ConfigDict
from sqlmodel import SQLModel, Field, Relationship

from src.teams.models import Team, TeamRead


# ---------------------------------------------------------------------------
# PredictTournament
# ---------------------------------------------------------------------------

class PredictTournament(SQLModel, table=True):
    __tablename__ = "predict_tournament"

    tournament_id: int = Field(
        sa_column=sa.Column(sa.Integer, sa.ForeignKey("tournament.id", ondelete="CASCADE"), primary_key=True, nullable=False)
    )
    user_id: int = Field(
        sa_column=sa.Column(sa.Integer, sa.ForeignKey("user.id", ondelete="CASCADE"), primary_key=True, nullable=False)
    )
    winner_team_id: Optional[int] = Field(
        default=None,
        sa_column=sa.Column(sa.Integer, sa.ForeignKey("team.id", ondelete="SET NULL"), nullable=True)
    )

    points_earned: Optional[int] = Field(
        default=None,
        sa_column=sa.Column(sa.Integer, nullable=True),
    )

    winner_team: Optional[Team] = Relationship(
        sa_relationship_kwargs={
            "primaryjoin": "PredictTournament.winner_team_id == Team.id",
            "foreign_keys": "[PredictTournament.winner_team_id]",
            "lazy": "selectin",
        }
    )


class PredictTournamentCreate(SQLModel):
    """Body for POST /predict/tournament — creates or updates the current user's prediction."""
    tournament_id: int
    winner_team_id: Optional[int] = None


class PredictTournamentRead(SQLModel):
    """Response model returned by tournament prediction endpoints."""
    model_config = ConfigDict(from_attributes=True)

    tournament_id: int
    user_id: int
    winner_team_id: Optional[int] = None
    winner_team: Optional[TeamRead] = None
    points_earned: Optional[int] = None


# ---------------------------------------------------------------------------
# PredictGroup
# ---------------------------------------------------------------------------

class PredictGroup(SQLModel, table=True):
    __tablename__ = "predict_group"

    group_id: int = Field(
        sa_column=sa.Column(sa.Integer, sa.ForeignKey("tournament_group.id", ondelete="CASCADE"), primary_key=True, nullable=False)
    )
    user_id: int = Field(
        sa_column=sa.Column(sa.Integer, sa.ForeignKey("user.id", ondelete="CASCADE"), primary_key=True, nullable=False)
    )
    winner_team_id: Optional[int] = Field(
        default=None,
        sa_column=sa.Column(sa.Integer, sa.ForeignKey("team.id", ondelete="SET NULL"), nullable=True)
    )

    points_earned: Optional[int] = Field(
        default=None,
        sa_column=sa.Column(sa.Integer, nullable=True),
    )

    winner_team: Optional[Team] = Relationship(
        sa_relationship_kwargs={
            "primaryjoin": "PredictGroup.winner_team_id == Team.id",
            "foreign_keys": "[PredictGroup.winner_team_id]",
            "lazy": "selectin",
        }
    )


class PredictGroupCreate(SQLModel):
    """Body for POST /predict/group — creates or updates the current user's prediction."""
    group_id: int
    winner_team_id: Optional[int] = None


class PredictGroupRead(SQLModel):
    """Response model returned by group prediction endpoints."""
    model_config = ConfigDict(from_attributes=True)

    group_id: int
    user_id: int
    winner_team_id: Optional[int] = None
    winner_team: Optional[TeamRead] = None
    points_earned: Optional[int] = None


# ---------------------------------------------------------------------------
# PredictStage
# ---------------------------------------------------------------------------

class PredictStage(SQLModel, table=True):
    __tablename__ = "predict_stage"

    stage_id: int = Field(
        sa_column=sa.Column(sa.Integer, sa.ForeignKey("stage.id", ondelete="CASCADE"), primary_key=True, nullable=False)
    )
    user_id: int = Field(
        sa_column=sa.Column(sa.Integer, sa.ForeignKey("user.id", ondelete="CASCADE"), primary_key=True, nullable=False)
    )
    winner_team_id: Optional[int] = Field(
        default=None,
        sa_column=sa.Column(sa.Integer, sa.ForeignKey("team.id", ondelete="SET NULL"), nullable=True)
    )

    points_earned: Optional[int] = Field(
        default=None,
        sa_column=sa.Column(sa.Integer, nullable=True),
    )

    winner_team: Optional[Team] = Relationship(
        sa_relationship_kwargs={
            "primaryjoin": "PredictStage.winner_team_id == Team.id",
            "foreign_keys": "[PredictStage.winner_team_id]",
            "lazy": "selectin",
        }
    )


class PredictStageCreate(SQLModel):
    """Body for POST /predict/stage — creates or updates the current user's prediction."""
    stage_id: int
    winner_team_id: Optional[int] = None


class PredictStageRead(SQLModel):
    """Response model returned by stage prediction endpoints."""
    model_config = ConfigDict(from_attributes=True)

    stage_id: int
    user_id: int
    winner_team_id: Optional[int] = None
    winner_team: Optional[TeamRead] = None
    points_earned: Optional[int] = None


# ---------------------------------------------------------------------------
# PredictMatch
# ---------------------------------------------------------------------------

class PredictMatch(SQLModel, table=True):
    __tablename__ = "predict_match"

    match_id: int = Field(
        sa_column=sa.Column(sa.Integer, sa.ForeignKey("match.id", ondelete="CASCADE"), primary_key=True, nullable=False)
    )
    user_id: int = Field(
        sa_column=sa.Column(sa.Integer, sa.ForeignKey("user.id", ondelete="CASCADE"), primary_key=True, nullable=False)
    )
    home_score: Optional[int] = Field(default=None, ge=0)
    away_score: Optional[int] = Field(default=None, ge=0)
    points_earned: Optional[int] = Field(
        default=None,
        sa_column=sa.Column(sa.Integer, nullable=True),
    )


class PredictMatchCreate(SQLModel):
    """Body for POST /predict/match — creates or updates the current user's prediction."""
    match_id: int
    home_score: Optional[int] = Field(default=None, ge=0)
    away_score: Optional[int] = Field(default=None, ge=0)


class PredictMatchRead(SQLModel):
    """Response model returned by match prediction endpoints."""
    model_config = ConfigDict(from_attributes=True)

    match_id: int
    user_id: int
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    points_earned: Optional[int] = None
