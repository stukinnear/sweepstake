from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Iterable, Optional

from sqlalchemy import false, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.groups_stages import models as groups_stages_models
from src.matches import models as match_models
from src.predictions import scoring as predictions_scoring
from src.providers.models import ProviderCompetition, ProviderMatch, ProviderTeam
from src.teams import models as team_models
from src.tournaments import models as tournament_models
from src.logging_config import get_logger

logger = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"


def _label(value: Optional[str]) -> Optional[str]:
    return None if value is None else value.replace("_", " ").title()


class FootballProvider(ABC):
    provider_id: str
    competition_format: tournament_models.CompetitionFormat = tournament_models.CompetitionFormat.tournament

    @abstractmethod
    async def list_competitions(self) -> list[ProviderCompetition]:
        raise NotImplementedError

    @abstractmethod
    async def fetch_matches(self, competition_id: str) -> tuple[dict, list[ProviderMatch]]:
        raise NotImplementedError

    async def fetch_teams(self, competition_id: str) -> list[ProviderTeam]:
        return []

    def expected_team_names(self, competition_id: str) -> set[str] | None:
        return None

    async def import_competition(
        self,
        db: AsyncSession,
        competition_id: str,
        tournament: tournament_models.Tournament,
    ) -> tournament_models.Tournament:
        _raw, matches = await self.fetch_matches(competition_id)
        provider_teams = await self.fetch_teams(competition_id)
        tournament.external_provider = self.provider_id
        tournament.external_id = str(competition_id)
        tournament.competition_format = self.competition_format
        if self.provider_id == "football-data-org" and str(competition_id).isdigit():
            tournament.football_data_org_id = int(competition_id)

        groups_seen: dict[str, int] = {}
        stages_seen: dict[str, int] = {}
        team_id_map: dict[str, int] = {}

        for provider_team in provider_teams:
            await self._get_or_create_team(db, tournament.id, provider_team, None, team_id_map)

        for provider_match in matches:
            group_id = await self._get_or_create_group(db, tournament.id, provider_match.group_name, groups_seen)
            await self._get_or_create_team(db, tournament.id, provider_match.home_team, group_id, team_id_map)
            await self._get_or_create_team(db, tournament.id, provider_match.away_team, group_id, team_id_map)

        for provider_match in matches:
            stage_id = await self._get_or_create_stage(db, tournament.id, provider_match.stage_name, stages_seen)
            db.add(
                match_models.Match(
                    external_provider=self.provider_id,
                    external_id=provider_match.external_id,
                    football_data_org_id=(
                        int(provider_match.external_id)
                        if self.provider_id == "football-data-org" and provider_match.external_id.isdigit()
                        else None
                    ),
                    tournament_id=tournament.id,
                    home_team_id=self._team_id(provider_match.home_team, team_id_map),
                    away_team_id=self._team_id(provider_match.away_team, team_id_map),
                    stage_id=stage_id,
                    start_datetime=provider_match.start_datetime,
                    home_goals=provider_match.home_goals,
                    away_goals=provider_match.away_goals,
                )
            )

        await db.commit()
        logger.info("Imported %s matches from %s competition %s", len(matches), self.provider_id, competition_id)
        return tournament

    async def update_competition(self, db: AsyncSession, competition_id: str) -> None:
        tournament_ids = await self._tournament_ids(db, competition_id)
        await self._set_update_status(
            db,
            tournament_ids,
            "running",
            f"Updating {self.provider_id} competition {competition_id}",
        )
        await db.commit()

        try:
            raw, matches = await self.fetch_matches(competition_id)
            provider_teams = await self.fetch_teams(competition_id)
            data_hash = hashlib.md5(str(raw).encode()).hexdigest()
            hash_file = _DATA_DIR / f"provider_hash_{self.provider_id}_{competition_id}.txt"
            legacy_hash_file = _DATA_DIR / f"football_data_hash_{competition_id}.txt"
        except Exception as exc:
            await self._set_update_status(db, tournament_ids, "failed", str(exc)[:512])
            await db.commit()
            raise

        if hash_file.is_file() and hash_file.read_text().strip() == data_hash:
            if self.provider_id == "thesportsdb" or await self._has_missing_team_images(db, tournament_ids):
                logger.info("No match changes for %s competition %s; refreshing team metadata.", self.provider_id, competition_id)
            else:
                logger.info("No changes detected for %s competition %s; skipping import.", self.provider_id, competition_id)
                await self._set_update_status(
                    db,
                    tournament_ids,
                    "success",
                    "No changes detected.",
                    match_count=len(matches),
                    team_count=len(provider_teams) if provider_teams else None,
                )
                await db.commit()
                return

        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        relevant_matches = [
            match for match in matches
            if match.status in {"TIMED", "SCHEDULED", "FINISHED", "LIVE", "IN_PLAY"}
            and (match.status != "FINISHED" or match.start_datetime >= cutoff)
        ]

        hash_unchanged = hash_file.is_file() and hash_file.read_text().strip() == data_hash
        await self._refresh_team_metadata(db, tournament_ids, matches, provider_teams, competition_id)
        if hash_unchanged and self.provider_id != "thesportsdb":
            await self._set_update_status(
                db,
                tournament_ids,
                "success",
                "No match changes; team metadata refreshed.",
                match_count=len(matches),
                team_count=len(provider_teams) if provider_teams else None,
            )
            await db.commit()
            return

        match_ids_to_rescore: list[int] = []
        for provider_match in relevant_matches:
            existing_matches = await self._matched_matches(db, provider_match.external_id)
            missing_tournament_ids = list(tournament_ids)

            for existing_match in existing_matches:
                if existing_match.tournament_id in missing_tournament_ids:
                    missing_tournament_ids.remove(existing_match.tournament_id)
                await self._apply_match_update(db, existing_match, provider_match)
                if provider_match.home_goals is not None and provider_match.away_goals is not None:
                    match_ids_to_rescore.append(existing_match.id)

            for tournament_id in missing_tournament_ids:
                await self._create_missing_match(db, tournament_id, provider_match)

        for match_id in match_ids_to_rescore:
            await predictions_scoring.recalculate_match_points(db, match_id)

        await self._set_update_status(
            db,
            tournament_ids,
            "success",
            "Provider update completed.",
            match_count=len(matches),
            team_count=len(provider_teams) if provider_teams else None,
        )
        await db.commit()
        hash_file.write_text(data_hash)
        if self.provider_id == "football-data-org":
            legacy_hash_file.write_text(data_hash)

    async def _set_update_status(
        self,
        db: AsyncSession,
        tournament_ids: list[int],
        status: str,
        message: str,
        match_count: int | None = None,
        team_count: int | None = None,
    ) -> None:
        for tournament_id in tournament_ids:
            tournament = await db.get(tournament_models.Tournament, tournament_id)
            if not tournament:
                continue
            tournament.provider_update_status = status
            tournament.provider_update_message = message
            tournament.provider_updated_at = datetime.now(timezone.utc)
            if match_count is not None:
                tournament.provider_update_match_count = match_count
            if team_count is not None:
                tournament.provider_update_team_count = team_count

    async def _has_missing_team_images(self, db: AsyncSession, tournament_ids: list[int]) -> bool:
        if not tournament_ids:
            return False
        result = await db.execute(
            select(team_models.Team.id)
            .where(team_models.Team.tournament_id.in_(tournament_ids))
            .where(team_models.Team.external_provider == self.provider_id)
            .where((team_models.Team.image_url.is_(None)) | (team_models.Team.image_url == ""))
            .limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def _refresh_team_metadata(
        self,
        db: AsyncSession,
        tournament_ids: list[int],
        matches: list[ProviderMatch],
        teams: list[ProviderTeam],
        competition_id: str,
    ) -> None:
        team_refs = 0
        team_refs_with_images = 0
        for tournament_id in tournament_ids:
            team_map: dict[str, int] = {}
            for provider_team in teams:
                team_refs += 1
                if provider_team.image_url:
                    team_refs_with_images += 1
                await self._get_or_create_team(db, tournament_id, provider_team, None, team_map)
            for provider_match in matches:
                for provider_team in (provider_match.home_team, provider_match.away_team):
                    if provider_team is None:
                        continue
                    team_refs += 1
                    if provider_team.image_url:
                        team_refs_with_images += 1
                await self._get_or_create_team(db, tournament_id, provider_match.home_team, None, team_map)
                await self._get_or_create_team(db, tournament_id, provider_match.away_team, None, team_map)
            await self._prune_unexpected_teams(db, tournament_id, self.expected_team_names(competition_id))
        logger.info(
            "%s team metadata refresh: tournaments=%s team_refs=%s team_refs_with_images=%s",
            self.provider_id,
            len(tournament_ids),
            team_refs,
            team_refs_with_images,
        )
        if tournament_ids:
            result = await db.execute(
                select(team_models.Team.image_url)
                .where(team_models.Team.tournament_id.in_(tournament_ids))
                .where(team_models.Team.external_provider == self.provider_id)
            )
            team_image_values = result.scalars().all()
            logger.info(
                "%s team image rows after refresh: teams=%s teams_with_images=%s",
                self.provider_id,
                len(team_image_values),
                sum(1 for image_url in team_image_values if image_url),
            )

    async def _prune_unexpected_teams(
        self,
        db: AsyncSession,
        tournament_id: int,
        expected_names: set[str] | None,
    ) -> None:
        if not expected_names:
            return
        result = await db.execute(
            select(team_models.Team)
            .where(team_models.Team.tournament_id == tournament_id)
            .where(team_models.Team.external_provider == self.provider_id)
        )
        unexpected_teams = [
            team for team in result.scalars().all()
            if team.name.casefold() not in expected_names
        ]
        for team in unexpected_teams:
            logger.info(
                "Removing unexpected %s team tournament_id=%s external_id=%s name=%r",
                self.provider_id,
                tournament_id,
                team.external_id,
                team.name,
            )
            await db.delete(team)

    async def _get_or_create_group(
        self,
        db: AsyncSession,
        tournament_id: int,
        group_name: Optional[str],
        groups_seen: dict[str, int],
    ) -> Optional[int]:
        name = _label(group_name)
        if name is None:
            return None
        if name in groups_seen:
            return groups_seen[name]
        group = groups_stages_models.Group(name=name, tournament_id=tournament_id)
        db.add(group)
        await db.flush()
        groups_seen[name] = group.id
        return group.id

    async def _get_or_create_stage(
        self,
        db: AsyncSession,
        tournament_id: int,
        stage_name: Optional[str],
        stages_seen: dict[str, int],
    ) -> Optional[int]:
        name = _label(stage_name)
        if name is None:
            return None
        if name in stages_seen:
            return stages_seen[name]
        stage = groups_stages_models.Stage(name=name, tournament_id=tournament_id)
        db.add(stage)
        await db.flush()
        stages_seen[name] = stage.id
        return stage.id

    async def _get_or_create_team(
        self,
        db: AsyncSession,
        tournament_id: int,
        provider_team: Optional[ProviderTeam],
        group_id: Optional[int],
        team_id_map: dict[str, int],
    ) -> Optional[team_models.Team]:
        if provider_team is None or provider_team.external_id is None:
            return None
        key = f"{tournament_id}:{provider_team.external_id}"
        if key in team_id_map:
            return await db.get(team_models.Team, team_id_map[key])
        result = await db.execute(
            select(team_models.Team)
            .where(team_models.Team.tournament_id == tournament_id)
            .where(team_models.Team.name == provider_team.name)
        )
        team = result.scalars().first()
        if team is None:
            result = await db.execute(
                select(team_models.Team)
                .where(team_models.Team.tournament_id == tournament_id)
                .where(
                    or_(
                        (team_models.Team.external_provider == self.provider_id)
                        & (team_models.Team.external_id == provider_team.external_id),
                        self._legacy_team_filter(provider_team.external_id),
                    )
                )
            )
            team = result.scalars().first()
        if team is None:
            team = team_models.Team(
                external_provider=self.provider_id,
                external_id=provider_team.external_id,
                football_data_org_id=(
                    int(provider_team.external_id)
                    if self.provider_id == "football-data-org" and provider_team.external_id.isdigit()
                    else None
                ),
                name=provider_team.name,
                iso_code=provider_team.iso_code,
                image_url=provider_team.image_url,
                tournament_id=tournament_id,
                group_id=group_id,
            )
            db.add(team)
            await db.flush()
            if provider_team.image_url:
                logger.info(
                    "Created %s team image tournament_id=%s external_id=%s name=%r",
                    self.provider_id,
                    tournament_id,
                    provider_team.external_id,
                    provider_team.name,
                )
        else:
            team.external_provider = self.provider_id
            team.external_id = provider_team.external_id
            team.name = provider_team.name
            team.iso_code = provider_team.iso_code
            if provider_team.image_url and team.image_url != provider_team.image_url:
                team.image_url = provider_team.image_url
                logger.info(
                    "Updated %s team image tournament_id=%s external_id=%s name=%r",
                    self.provider_id,
                    tournament_id,
                    provider_team.external_id,
                    provider_team.name,
                )
            if group_id is not None:
                team.group_id = group_id
        team_id_map[key] = team.id
        return team

    def _team_id(self, provider_team: Optional[ProviderTeam], team_id_map: dict[str, int]) -> Optional[int]:
        if provider_team is None or provider_team.external_id is None:
            return None
        return team_id_map.get(f"{provider_team.external_id}") or next(
            (team_id for key, team_id in team_id_map.items() if key.endswith(f":{provider_team.external_id}")),
            None,
        )

    async def _matched_matches(self, db: AsyncSession, external_id: str) -> list[match_models.Match]:
        result = await db.execute(
            select(match_models.Match).where(
                or_(
                    (match_models.Match.external_provider == self.provider_id)
                    & (match_models.Match.external_id == external_id),
                    self._legacy_match_filter(external_id),
                )
            )
        )
        return result.scalars().all()

    async def _tournament_ids(self, db: AsyncSession, competition_id: str) -> list[int]:
        result = await db.execute(
            select(tournament_models.Tournament.id).where(
                or_(
                    (tournament_models.Tournament.external_provider == self.provider_id)
                    & (tournament_models.Tournament.external_id == str(competition_id)),
                    self._legacy_tournament_filter(competition_id),
                )
            )
        )
        return result.scalars().all()

    async def _apply_match_update(
        self,
        db: AsyncSession,
        existing_match: match_models.Match,
        provider_match: ProviderMatch,
    ) -> None:
        team_map: dict[str, int] = {}
        home_team = await self._get_or_create_team(db, existing_match.tournament_id, provider_match.home_team, None, team_map)
        away_team = await self._get_or_create_team(db, existing_match.tournament_id, provider_match.away_team, None, team_map)
        existing_match.external_provider = self.provider_id
        existing_match.external_id = provider_match.external_id
        existing_match.start_datetime = provider_match.start_datetime
        existing_match.home_goals = provider_match.home_goals
        existing_match.away_goals = provider_match.away_goals
        existing_match.home_team_id = home_team.id if home_team else None
        existing_match.away_team_id = away_team.id if away_team else None

    async def _create_missing_match(
        self,
        db: AsyncSession,
        tournament_id: int,
        provider_match: ProviderMatch,
    ) -> None:
        team_map: dict[str, int] = {}
        home_team = await self._get_or_create_team(db, tournament_id, provider_match.home_team, None, team_map)
        away_team = await self._get_or_create_team(db, tournament_id, provider_match.away_team, None, team_map)
        db.add(
            match_models.Match(
                external_provider=self.provider_id,
                external_id=provider_match.external_id,
                tournament_id=tournament_id,
                start_datetime=provider_match.start_datetime,
                home_goals=provider_match.home_goals,
                away_goals=provider_match.away_goals,
                home_team_id=home_team.id if home_team else None,
                away_team_id=away_team.id if away_team else None,
            )
        )

    def _legacy_tournament_filter(self, competition_id: str):
        return false()

    def _legacy_team_filter(self, external_id: str):
        return false()

    def _legacy_match_filter(self, external_id: str):
        return false()
