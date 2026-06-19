import asyncio, datetime, random

from sqlalchemy import text

from src.database import AsyncSessionLocal, _IS_SQLITE
from src.users import crud as user_crud
from src.users.models import UserCreate
from src.logging_config import get_logger
from src.matches import crud as match_crud
from src.tournaments import crud as tournament_crud
from src.teams import crud as team_crud
from src.groups_stages import crud as groups_stages_crud
from src.predictions import crud as prediction_crud
from src.tournaments import crud as tournament_crud, models as tournament_models
from src.predictions.models import PredictTournamentCreate, PredictGroupCreate, PredictStageCreate, PredictMatchCreate

logger = get_logger(__name__)

_GOAL_CHOICE_LST = [0, 1, 2, 3]

_LOAD_TEST_DATA_LOCK_KEY = 20260510


async def load_test_data() -> None:
    async with AsyncSessionLocal() as db:
        # Advisory lock serialises this across multiple gunicorn workers so the
        # "user already exists" guard can't race between a check and the first commit.
        # SQLite has single-writer semantics, so the lock is unnecessary there.
        if not _IS_SQLITE:
            await db.execute(text(f"SELECT pg_advisory_lock({_LOAD_TEST_DATA_LOCK_KEY})"))
        try:
            existing = await user_crud.get_user_by_email(db, "test@example.com")
            if existing is not None:
                logger.info("Test user already exists, skipping creation.")
                return

            # Create test user 1 that is trounament admin
            user = await user_crud.create_user(
                db,
                UserCreate(
                    email="test@example.com",
                    password="Password",
                    first_name="Test",
                    last_name="User",
                    #user_name="testuser",
                    gender=None,
                ),
            )
            logger.info(f"Test user created: {user.email}")

            # Create tournament and use 2026 Fifa Worldcup as source but move match dates to around now
            tournament = await tournament_crud.create_tournament(
                db,
                tournament_models.TournamentCreate(
                    name="TEST FIFA World Cup 2026",
                    football_data_org_id=2000,
                ),
                user.id,
            )
            matches = await match_crud.get_matches_by_tournament(db, tournament.id)
            matches_with_teams = [
                m for m in matches
                if m.home_team_id is not None and m.away_team_id is not None
            ]
            selected_match_datetime = matches[len(matches_with_teams) // 3].start_datetime
            datetime_offset = datetime.timedelta(days=(datetime.datetime.now(tz=selected_match_datetime.tzinfo) - selected_match_datetime).days)
            now = datetime.datetime.now(tz=selected_match_datetime.tzinfo)
            for match in matches:
                match.start_datetime += datetime_offset
                match.tv_channel = random.choice(["Channel A", "Channel B", "Channel C", None, ""])
                if match.start_datetime < now:
                    match.home_goals = random.choice(_GOAL_CHOICE_LST)
                    match.away_goals = random.choice(_GOAL_CHOICE_LST)
            await db.commit()

            logger.info(f"Test tournament data imported from Football Data API: {tournament.name}")

            # Create test user 2 that is a normal trounament partciapant
            user2 = await user_crud.create_user(
                db,
                UserCreate(
                    email="test2@example.com",
                    password="Password",
                    first_name="Test2",
                    last_name="User2",
                    #user_name="testuser2",
                    gender=None,
                ),
            )

            await tournament_crud.join_tournament(db, tournament_join_code=tournament.join_code, user_id=user2.id)  # returns (tournament, already_member)
            logger.info(f"Test user2 created: {user2.email}")

            # Get list of all teams in the tournament
            teams = await team_crud.get_teams_by_tournament(db, tournament.id)
            logger.info(f"Teams in tournament ({len(teams)}): {[t.name for t in teams]}")

            groups = await groups_stages_crud.get_groups_by_tournament(db, tournament.id)
            stages = await groups_stages_crud.get_stages_by_tournament(db, tournament.id)

            for u in [user, user2]:
                winning_team = random.choice(teams)
                await prediction_crud.upsert_predict_tournament(
                    db,
                    PredictTournamentCreate(
                        tournament_id=tournament.id,
                        winner_team_id=winning_team.id,
                    ),
                    user_id=u.id,
                )
                logger.info(f"Tournament prediction created for {u.email}: {winning_team.name}")

                for group in groups:
                    if random.choice([True, False]):
                        group_team = random.choice(teams)
                        await prediction_crud.upsert_predict_group(
                            db,
                            PredictGroupCreate(group_id=group.id, winner_team_id=group_team.id),
                            user_id=u.id,
                        )
                        logger.info(f"Group prediction created for {u.email} group {group.id}: {group_team.name}")

                for stage in stages:
                    if random.choice([True, True, True, False, False]):
                        stage_team = random.choice(teams)
                        await prediction_crud.upsert_predict_stage(
                            db,
                            PredictStageCreate(stage_id=stage.id, winner_team_id=stage_team.id),
                            user_id=u.id,
                        )
                        logger.info(f"Stage prediction created for {u.email} stage {stage.id}: {stage_team.name}")

                for match in matches_with_teams:
                    if random.choice([True, True, True, False, False]):
                        await prediction_crud.upsert_predict_match(
                            db,
                            PredictMatchCreate(
                                match_id=match.id,
                                home_score=random.choice(_GOAL_CHOICE_LST),
                                away_score=random.choice(_GOAL_CHOICE_LST),
                            ),
                            user_id=u.id,
                        )
                        logger.info(f"Match prediction created for {u.email} match {match.id}")

            await db.commit()

        finally:
            if not _IS_SQLITE:
                await db.execute(text(f"SELECT pg_advisory_unlock({_LOAD_TEST_DATA_LOCK_KEY})"))

    
