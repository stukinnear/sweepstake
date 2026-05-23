"""Shared test fixtures for the sweepstake test suite."""

import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from fastapi import Request
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel

from src.main import app
from src.database import get_db
from src.users.routers import verify_access_token
from src.users.models import User
from src.users.utils import hash_password
from src.predictions import scoring as predictions_scoring


# In-memory SQLite for fast, isolated tests
TEST_DATABASE_URL = "sqlite+aiosqlite://"


USER_1_PAYLOAD = {
    "id": 1,
    "email": "test@example.com",
    "password": "not_very_real",
    "first_name": "Test",
}

USER_2_PAYLOAD = {
    "id": 2,
    "email": "other@example.com",
    "password": "not_extremely_real",
    "first_name": "Other",
}


@pytest.fixture(scope="session")
def event_loop():
    """Create a single event loop for the whole test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture()
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh in-memory database and session for each test."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    original_scoring_factory = predictions_scoring._session_factory
    predictions_scoring._session_factory = session_factory

    async with session_factory() as session:
        # Seed a test user so FK relationships resolve correctly
        session.add(User(**USER_1_PAYLOAD, hashed_password=hash_password(USER_1_PAYLOAD["password"])))
        session.add(User(**USER_2_PAYLOAD, hashed_password=hash_password(USER_2_PAYLOAD["password"])))
        await session.commit()
        yield session

    predictions_scoring._session_factory = original_scoring_factory

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
    await engine.dispose()


def _fake_verify_access_token(request: Request) -> dict:
    """Override that reads the test user id from an X-Test-User header."""
    uid = int(request.headers.get("X-Test-User", USER_1_PAYLOAD["id"]))
    return {"uid": uid, "type": "access"}


@pytest_asyncio.fixture()
async def client_user_1(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Provide an authenticated httpx AsyncClient wired to the test DB (user 1)."""

    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[verify_access_token] = _fake_verify_access_token

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"X-Test-User": str(USER_1_PAYLOAD["id"])},
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture()
async def client_unauth(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Provide an httpx AsyncClient with NO auth override — uses real cookie-based auth.

    Use this for testing the full auth flow: register → login → make
    authenticated requests using the cookies the server sets.
    """

    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    # No verify_access_token override — real JWT cookies are used

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture()
async def client_user_2(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Provide an authenticated httpx AsyncClient acting as user 2."""

    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[verify_access_token] = _fake_verify_access_token

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"X-Test-User": str(USER_2_PAYLOAD["id"])},
    ) as ac:
        yield ac

    app.dependency_overrides.clear()
