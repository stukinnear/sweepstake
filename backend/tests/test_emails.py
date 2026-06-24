import pytest
from httpx import AsyncClient

from src.emails import send as email_send

pytestmark = pytest.mark.asyncio


async def test_send_email_saves_test_address(tmp_path, monkeypatch):
    monkeypatch.setattr(email_send, "_DATA_DIR", tmp_path)

    await email_send.send_email(
        "person@example.com",
        "Test subject",
        "<p>Hello</p>",
        "Hello",
        user_id=123,
    )

    saved = tmp_path / "test_email_person_123.html"
    assert saved.exists()
    assert saved.read_text(encoding="utf-8") == "<p>Hello</p>"


async def test_send_email_uses_smtp_when_configured(monkeypatch):
    sent = []

    async def fake_to_thread(func, *args):
        sent.append((func, args))

    monkeypatch.setattr(email_send.settings, "email_host", "smtp.example.test")
    monkeypatch.setattr(email_send.asyncio, "to_thread", fake_to_thread)

    await email_send.send_email(
        "person@real.test",
        "SMTP subject",
        "<p>Hello</p>",
        "Hello",
        reply_to="Admin <admin@example.com>",
    )

    assert len(sent) == 1
    assert sent[0][1] == (
        "person@real.test",
        "SMTP subject",
        "<p>Hello</p>",
        "Hello",
        "Admin <admin@example.com>",
    )


async def test_forgot_password_existing_email_sends_reset_email(client_unauth: AsyncClient, monkeypatch):
    sent = []

    async def fake_send_password_reset_email(to_email: str, reset_link: str, first_name: str = "there"):
        sent.append((to_email, reset_link, first_name))

    monkeypatch.setattr("src.users.routers.send_password_reset_email", fake_send_password_reset_email)

    response = await client_unauth.post("/auth/forgot-password", json={"email": "test@example.com"})

    assert response.status_code == 200
    assert len(sent) == 1
    assert sent[0][0] == "test@example.com"
    assert sent[0][1].startswith("http")
    assert sent[0][2] == "Test"


async def test_forgot_password_unknown_email_does_not_send(client_unauth: AsyncClient, monkeypatch):
    sent = []

    async def fake_send_password_reset_email(*args, **kwargs):
        sent.append((args, kwargs))

    monkeypatch.setattr("src.users.routers.send_password_reset_email", fake_send_password_reset_email)

    response = await client_unauth.post("/auth/forgot-password", json={"email": "missing@example.com"})

    assert response.status_code == 200
    assert sent == []


async def test_create_tournament_sends_welcome_email(client_user_1: AsyncClient, monkeypatch):
    sent = []

    async def fake_send_competition_welcome_email(**kwargs):
        sent.append(kwargs)

    monkeypatch.setattr("src.tournaments.routers.send_competition_welcome_email", fake_send_competition_welcome_email)

    response = await client_user_1.post("/tournament", json={"name": "Email Cup", "stake": "Five pounds"})

    assert response.status_code == 201
    assert len(sent) == 1
    assert sent[0]["to_email"] == "test@example.com"
    assert sent[0]["first_name"] == "Test"
    assert sent[0]["tournament_name"] == "Email Cup"
    assert sent[0]["stake"] == "Five pounds"
    assert sent[0]["has_group_stage_predictions"] is True


async def test_join_tournament_sends_welcome_email(client_user_1: AsyncClient, client_user_2: AsyncClient, monkeypatch):
    sent = []

    async def fake_send_competition_welcome_email(**kwargs):
        sent.append(kwargs)

    monkeypatch.setattr("src.tournaments.routers.send_competition_welcome_email", fake_send_competition_welcome_email)

    create_response = await client_user_1.post("/tournament", json={"name": "Join Email Cup"})
    join_code = create_response.json()["join_code"]

    response = await client_user_2.post(f"/tournament/join/{join_code}")

    assert response.status_code == 200
    assert [item["to_email"] for item in sent] == ["test@example.com", "other@example.com"]
    assert sent[-1]["first_name"] == "Other"


async def test_payment_reminder_sends_only_to_unpaid_participants(
    client_user_1: AsyncClient,
    client_user_2: AsyncClient,
    monkeypatch,
):
    sent = []

    async def fake_send_payment_reminder_email(**kwargs):
        sent.append(kwargs)

    monkeypatch.setattr("src.tournaments.routers.send_payment_reminder_email", fake_send_payment_reminder_email)
    monkeypatch.setattr("src.tournaments.routers._email_wait", lambda _n: 0)

    create_response = await client_user_1.post(
        "/tournament",
        json={"name": "Payment Cup", "stake": "Five pounds"},
    )
    tournament = create_response.json()
    await client_user_2.post(f"/tournament/join/{tournament['join_code']}")
    await client_user_1.patch(
        f"/tournament/{tournament['id']}/stake-paid",
        json={"user_id": 1, "stake_paid": True},
    )

    response = await client_user_1.post(
        f"/tournament/{tournament['id']}/action",
        json={"action": "send-payment-reminder"},
    )

    assert response.status_code == 204
    assert [item["to_email"] for item in sent] == ["other@example.com"]
    assert sent[0]["first_name"] == "Other"
    assert sent[0]["stake"] == "Five pounds"


async def test_resend_welcome_email_admin_action_sends_to_all_participants(
    client_user_1: AsyncClient,
    client_user_2: AsyncClient,
    monkeypatch,
):
    sent = []

    async def fake_send_competition_welcome_email(**kwargs):
        sent.append(kwargs)

    monkeypatch.setattr("src.tournaments.routers.send_competition_welcome_email", fake_send_competition_welcome_email)
    monkeypatch.setattr("src.tournaments.routers._email_wait", lambda _n: 0)

    create_response = await client_user_1.post("/tournament", json={"name": "Welcome Cup"})
    tournament = create_response.json()
    await client_user_2.post(f"/tournament/join/{tournament['join_code']}")
    sent.clear()

    response = await client_user_1.post(
        f"/tournament/{tournament['id']}/action",
        json={"action": "send-welcome-email"},
    )

    assert response.status_code == 204
    assert [item["to_email"] for item in sent] == ["test@example.com", "other@example.com"]


async def test_welcome_email_hides_group_stage_copy_for_league_tournament(monkeypatch):
    from src.emails.welcome_email import send_competition_welcome_email

    sent = []

    async def fake_send_email(to_email, subject, html_body, text_body, **kwargs):
        sent.append({"html": html_body, "text": text_body})

    monkeypatch.setattr("src.emails.welcome_email.send_email", fake_send_email)

    await send_competition_welcome_email(
        to_email="person@example.com",
        first_name="Test",
        tournament_name="SPFL",
        tournament_id=1,
        stake=None,
        match_winner_points=3,
        match_score_points=5,
        group_winner_points=8,
        stage_winner_points=10,
        first_place_points=25,
        second_place_points=15,
        third_place_points=None,
        has_group_stage_predictions=False,
    )

    assert "Correct group winner" not in sent[0]["text"]
    assert "Correct stage/round winner" not in sent[0]["text"]
    assert "Tournament winner predictions" in sent[0]["text"]
    assert "Tournament Winner Predictions" in sent[0]["html"]
    assert "Correct group winner" not in sent[0]["html"]
    assert "Correct stage / round winner" not in sent[0]["html"]


async def test_upcoming_email_hides_group_stage_deadline_for_league_tournament(monkeypatch):
    from src.emails.upcoming_matches_email import send_upcoming_matches_email

    sent = []

    async def fake_send_email(to_email, subject, html_body, text_body, **kwargs):
        sent.append({"html": html_body, "text": text_body})

    monkeypatch.setattr("src.emails.upcoming_matches_email.send_email", fake_send_email)

    await send_upcoming_matches_email(
        to_email="person@example.com",
        first_name="Test",
        tournament_name="SPFL",
        tournament_id=1,
        matches=[
            {
                "date_line": "Sat",
                "time_line": "15:00",
                "home_team_name": "Dundee",
                "home_team_image_url": None,
                "away_team_name": "Celtic",
                "away_team_image_url": None,
                "pred_home_score": None,
                "pred_away_score": None,
                "tv_channel": None,
            }
        ],
        winner_reminder={"has_tournament": True, "has_groups": False, "has_stages": False},
    )

    assert "tournament winner prediction" in sent[0]["text"]
    assert "Group Winners" not in sent[0]["text"]
    assert "Stage Winners" not in sent[0]["text"]
    assert "Your tournament winner prediction closes" in sent[0]["html"]
    assert "Group Winners" not in sent[0]["html"]
    assert "Stage Winners" not in sent[0]["html"]
