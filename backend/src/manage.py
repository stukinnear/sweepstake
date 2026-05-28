"""Management CLI for use inside the Docker container.

Usage (from /app/backend inside the container):
  /venv/bin/python src/manage.py <command> [args]

Commands:
  shell                        — interactive shell with DB session and helpers pre-loaded
  welcome_email <t_id> <u_id>  — send (or re-send) the welcome email for a tournament/user pair
  upcoming_reminders           — immediately run the upcoming-matches reminder job (normally fires at 15:00)
"""
import argparse
import asyncio
import sys
import threading
from pathlib import Path

# Insert backend/ onto sys.path so `src.*` imports resolve when the script is
# run directly (e.g. `python src/manage.py`), where sys.path[0] would otherwise
# be set to the src/ directory itself.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.database import AsyncSessionLocal
from src.tournaments.crud import get_tournament_by_id
from src.users.crud import get_user_by_id, get_user_by_email
from src.emails.welcome_email import send_competition_welcome_email


# ---------------------------------------------------------------------------
# welcome_email
# ---------------------------------------------------------------------------

async def _cmd_welcome_email(tournament_id: int, user_id: int) -> None:
    async with AsyncSessionLocal() as db:
        tournament = await get_tournament_by_id(db, tournament_id)
        if tournament is None:
            print(f"Error: tournament {tournament_id} not found.", file=sys.stderr)
            sys.exit(1)
        user = await get_user_by_id(db, user_id)
        if user is None:
            print(f"Error: user {user_id} not found.", file=sys.stderr)
            sys.exit(1)
        admins = [
            {"first_name": a.first_name, "last_name": a.last_name, "email": a.email}
            for a in tournament.admins
        ]
        await send_competition_welcome_email(
            to_email=user.email,
            first_name=user.first_name,
            tournament_name=tournament.name,
            tournament_id=tournament.id,
            stake=tournament.stake,
            match_winner_points=tournament.match_winner_points,
            match_score_points=tournament.match_score_points,
            group_winner_points=tournament.group_winner_points,
            stage_winner_points=tournament.stage_winner_points,
            first_place_points=tournament.first_place_points,
            second_place_points=tournament.second_place_points,
            third_place_points=tournament.third_place_points,
            admins=admins,
            user_id=user.id,
        )
        print(f"Welcome email sent to {user.email} for tournament '{tournament.name}'.")


# ---------------------------------------------------------------------------
# upcoming_reminders
# ---------------------------------------------------------------------------

async def _cmd_upcoming_reminders() -> None:
    from src.scheduler import _send_upcoming_match_reminders
    print("Running upcoming-matches reminder job…")
    await _send_upcoming_match_reminders()
    print("Done.")


# ---------------------------------------------------------------------------
# shell
# ---------------------------------------------------------------------------

_SHELL_BANNER = """\
SweepStake shell  (type exit() or Ctrl-D to quit)

Simple queries (related IDs auto-loaded):
  query(User)                               all users
  query(Tournament)                         all tournaments (incl. .admins, .participants,
                                              .participant_links, .matches)
  query(TournamentParticipantLink)          every tournament↔user participation row
  query(TournamentAdminLink)                every tournament↔admin row

Filtered queries:
  get_user_by_id(id)
  get_user_by_email(email)
  get_tournament_by_id(id)
  get_user_tournaments(user_id)             tournaments a user participates in

Custom queries:
  run(db.execute(
      select(User).where(User.id == 1)
  )).scalars().all()
  run(db.execute(
      select(TournamentParticipantLink).where(TournamentParticipantLink.user_id == 1)
  )).scalars().all()

  Available: db, run, select, where, User, Tournament,
             TournamentParticipantLink, TournamentAdminLink

Management commands:
  welcome_email(tournament_id, user_id)
  upcoming_reminders()                      run the upcoming-matches reminder job now
"""


async def _cmd_shell() -> None:
    import code
    from sqlalchemy import select
    from src.users.models import User
    from src.tournaments.models import Tournament, TournamentParticipantLink, TournamentAdminLink

    async with AsyncSessionLocal() as db:
        loop = asyncio.get_running_loop()

        def run(coro):
            """Submit a coroutine to the live event loop and block until done."""
            return asyncio.run_coroutine_threadsafe(coro, loop).result()

        def welcome_email(tournament_id: int, user_id: int) -> None:
            """Send the welcome email: welcome_email(tournament_id, user_id)"""
            tournament = run(get_tournament_by_id(db, tournament_id))
            if tournament is None:
                print(f"Error: tournament {tournament_id} not found.")
                return
            user = run(get_user_by_id(db, user_id))
            if user is None:
                print(f"Error: user {user_id} not found.")
                return
            admins = [
                {"first_name": a.first_name, "last_name": a.last_name, "email": a.email}
                for a in tournament.admins
            ]
            run(send_competition_welcome_email(
                to_email=user.email,
                first_name=user.first_name,
                tournament_name=tournament.name,
                tournament_id=tournament.id,
                stake=tournament.stake,
                match_winner_points=tournament.match_winner_points,
                match_score_points=tournament.match_score_points,
                group_winner_points=tournament.group_winner_points,
                stage_winner_points=tournament.stage_winner_points,
                first_place_points=tournament.first_place_points,
                second_place_points=tournament.second_place_points,
                third_place_points=tournament.third_place_points,
                admins=admins,
                user_id=user.id,
            ))
            print(f"Welcome email sent to {user.email} for tournament '{tournament.name}'.")

        def query(model):
            """Fetch all rows for a model: query(User) / query(Tournament)"""
            return run(db.execute(select(model))).scalars().all()

        def get_user_tournaments(user_id: int):
            """Return all TournamentParticipantLink rows for a user."""
            return run(
                db.execute(
                    select(TournamentParticipantLink).where(
                        TournamentParticipantLink.user_id == user_id
                    )
                )
            ).scalars().all()

        def upcoming_reminders() -> None:
            """Run the upcoming-matches reminder job now: upcoming_reminders()"""
            run(_cmd_upcoming_reminders())

        namespace = {
            "db": db,
            "run": run,
            "query": query,
            # convenience wrappers (no need to pass db or run())
            "get_user_by_id": lambda uid: run(get_user_by_id(db, uid)),
            "get_user_by_email": lambda email: run(get_user_by_email(db, email)),
            "get_tournament_by_id": lambda tid: run(get_tournament_by_id(db, tid)),
            "get_user_tournaments": get_user_tournaments,
            # management commands
            "welcome_email": welcome_email,
            "upcoming_reminders": upcoming_reminders,
            # ad-hoc query building
            "select": select,
            "User": User,
            "Tournament": Tournament,
            "TournamentParticipantLink": TournamentParticipantLink,
            "TournamentAdminLink": TournamentAdminLink,
        }

        done = threading.Event()

        def _interact():
            try:
                code.interact(banner=_SHELL_BANNER, local=namespace, exitmsg="")
            finally:
                done.set()

        t = threading.Thread(target=_interact, daemon=True)
        t.start()
        while not done.is_set():
            await asyncio.sleep(0.05)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="manage.py",
        description="SweepStake management commands",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("shell", help="Interactive shell with DB session and helpers pre-loaded")

    p = sub.add_parser("welcome_email", help="Send (or re-send) the welcome email to a user for a tournament")
    p.add_argument("tournament_id", type=int, help="Tournament ID")
    p.add_argument("user_id", type=int, help="User ID")

    sub.add_parser("upcoming_reminders", help="Run the upcoming-matches reminder job now (normally fires at 15:00)")

    args = parser.parse_args()

    if args.command == "shell":
        asyncio.run(_cmd_shell())
    elif args.command == "welcome_email":
        asyncio.run(_cmd_welcome_email(args.tournament_id, args.user_id))
    elif args.command == "upcoming_reminders":
        asyncio.run(_cmd_upcoming_reminders())


if __name__ == "__main__":
    main()
