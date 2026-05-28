from datetime import datetime, timezone, timedelta
from hmac import compare_digest
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete as sa_delete
from jose import jwt

from src.users.models import Session as SessionModel
from src.users import models
from src.users.utils import hash_password, verify_password, verify_token, SECRET_KEY, ALGORITHM

# ============================================================================
# User session operations
# ============================================================================

async def create_session(db: AsyncSession, user_id: int, session_id: str) -> SessionModel:
    """
    Create a new session for a user.
    """
    session = SessionModel(
        id=session_id,
        user_id=user_id,
        created_at=datetime.utcnow(),
        revoked=False,
        last_refresh=None,
    )
    db.add(session)
    await db.commit()
    return session

async def revoke_session(db: AsyncSession, session_id: str) -> Optional[SessionModel]:
    """
    Revoke a session by setting its revoked flag to True.
    """
    result = await db.execute(select(SessionModel).where(SessionModel.id == session_id))
    session = result.scalar_one_or_none()
    if session:
        session.revoked = True
        await db.commit()
    return session

async def get_session(db: AsyncSession, session_id: str) -> Optional[SessionModel]:
    """
    Retrieve a session by its ID.
    """
    result = await db.execute(select(SessionModel).where(SessionModel.id == session_id))
    return result.scalar_one_or_none()

async def revoke_all_user_sessions(db: AsyncSession, user_id: int) -> None:
    """
    Revoke all active sessions for a user (e.g. after a password change).
    """
    result = await db.execute(
        select(SessionModel).where(SessionModel.user_id == user_id, SessionModel.revoked == False)  # noqa: E712
    )
    sessions = result.scalars().all()
    for session in sessions:
        session.revoked = True
    await db.commit()


async def delete_old_sessions(db: AsyncSession) -> int:
    """Delete stale sessions: revoked sessions older than 30 days and all sessions older than 90 days."""
    cutoff_revoked = datetime.utcnow() - timedelta(days=30)
    cutoff_all = datetime.utcnow() - timedelta(days=90)
    result = await db.execute(
        sa_delete(SessionModel).where(
            ((SessionModel.revoked == True) & (SessionModel.created_at < cutoff_revoked))  # noqa: E712
            | (SessionModel.created_at < cutoff_all)
        )
    )
    await db.commit()
    return result.rowcount


async def rotate_session(db: AsyncSession, old_session_id: str, user_id: int, new_session_id: str) -> SessionModel:
    """
    Revoke the old session and create a new session for the user.
    """
    await revoke_session(db, old_session_id)
    return await create_session(db, user_id, new_session_id)


# ============================================================================
# User CRUD operations
# ============================================================================

async def get_user_by_email(db: AsyncSession, email: str) -> Optional[models.User]:
    """
    Get a user by email address.
    """
    result = await db.execute(select(models.User).where(models.User.email == email.lower()))
    return result.scalars().first()


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[models.User]:
    """
    Get a user by ID.
    """
    return await db.get(models.User, user_id)


async def create_user(db: AsyncSession, user: models.UserCreate) -> models.User:
    """
    Create a new user with a hashed password.
    """
    hashed_password = hash_password(user.password)

    if user.user_name:
        user_name = user.user_name
    elif user.last_name:
        import re
        parts = re.split(r"[ \-]", user.last_name)
        last_abbr = ".".join(p[0] for p in parts if p) + "."
        user_name = f"{user.first_name} {last_abbr}"
    else:
        user_name = user.first_name

    db_user = models.User(
        email=user.email.lower(),
        hashed_password=hashed_password,
        first_name=user.first_name,
        last_name=user.last_name,
        user_name=user_name,
        gender=user.gender,
        is_active=True,
        is_superuser=False,
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user


async def authenticate_user(
    db: AsyncSession,
    email: str,
    password: str
) -> Optional[models.User]:
    """
    Authenticate a user by email and password.
    Returns the user object if authentication succeeds, None otherwise.
    """
    user = await get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    if not user.is_active:
        return None
    return user


async def set_user_password(
    db: AsyncSession,
    user_id: int,
    new_password: str
) -> Optional[models.User]:
    """
    Set a new password for a user.
    """
    user = await get_user_by_id(db, user_id)
    if not user:
        return None
    user.hashed_password = hash_password(new_password)
    await db.commit()
    await db.refresh(user)
    return user


async def update_user(
    db: AsyncSession,
    user_id: int,
    user_update: models.UserUpdate
) -> Optional[models.User]:
    """
    Update user fields (email, is_active, is_superuser, etc.).
    """
    user = await get_user_by_id(db, user_id)
    if not user:
        return None
    update_data = user_update.model_dump(exclude_unset=True)
    if "email" in update_data:
        update_data["email"] = update_data["email"].lower()
    for field, value in update_data.items():
        setattr(user, field, value)
    await db.commit()
    await db.refresh(user)
    return user


async def delete_user(db: AsyncSession, user_id: int) -> Optional[models.User]:
    """
    Delete a user by ID.
    """
    user = await db.get(models.User, user_id)
    if user:
        db.delete(user)
        await db.commit()
    return user


async def delete_account(db: AsyncSession, user_id: int) -> None:
    """
    Delete a user account with all associated data.

    Sessions have no DB-level cascade so they are deleted explicitly.
    Admin links are deleted via the ORM so the after_flush event listener can
    auto-delete any tournament that loses its last admin.
    Predictions and participant links carry ondelete="CASCADE" and are removed
    automatically when the user row is deleted.
    """
    from src.tournaments.models import TournamentAdminLink

    sessions = (
        await db.execute(select(SessionModel).where(SessionModel.user_id == user_id))
    ).scalars().all()
    for s in sessions:
        await db.delete(s)

    admin_links = (
        await db.execute(
            select(TournamentAdminLink).where(TournamentAdminLink.user_id == user_id)
        )
    ).scalars().all()
    for link in admin_links:
        await db.delete(link)

    await db.flush()

    user = await db.get(models.User, user_id)
    if user:
        await db.delete(user)

    await db.commit()


# ============================================================================
# Password reset token operations
# ============================================================================

async def create_password_reset_token(
    db: AsyncSession, user_id: int, token: str, expire_minutes: int
) -> None:
    """Store a JWT-encoded password reset token on the user row."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)
    encoded = jwt.encode(
        {"sub": token, "uid": user_id, "exp": expire, "type": "reset"},
        SECRET_KEY,
        algorithm=ALGORITHM,
    )
    user = await db.get(models.User, user_id)
    if user:
        user.password_reset_token = encoded
        await db.commit()


async def get_valid_password_reset_token(
    db: AsyncSession, token: str
) -> Optional[models.User]:
    """Return the user if they hold a matching, non-expired JWT reset token."""
    result = await db.execute(
        select(models.User).where(models.User.password_reset_token.isnot(None))
    )
    for user in result.scalars().all():
        payload = verify_token(user.password_reset_token, token_type="reset")
        if payload is None:
            continue
        if compare_digest(payload.get("sub", ""), token):
            return user
    return None


async def clear_password_reset_token(
    db: AsyncSession, user_id: int
) -> None:
    """Clear the reset token after successful use."""
    user = await db.get(models.User, user_id)
    if user:
        user.password_reset_token = None
        await db.commit()
