from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlmodel import SQLModel, create_engine as create_sync_engine
from sqlalchemy import create_engine, text
from sqlalchemy.engine.url import make_url
from src.config import settings
from src.logging_config import get_logger

logger = get_logger(__name__)

DATABASE_URL = settings.database_url


def ensure_database_exists(database_url: str) -> None:
    """Connect to the server-level database (postgres) and create the
    target database if it doesn't exist.

    This uses a synchronous SQLAlchemy engine because CREATE DATABASE cannot
    run inside a transaction when using the async engine.
    """
    try:
        url = make_url(database_url)
        dbname = url.database
        if not dbname:
            return

        # Use the synchronous driver (drop any async driver suffix)
        driver = url.drivername.split("+")[0]
        user = url.username or ""
        password = url.password or ""
        host = url.host or "localhost"
        port = f":{url.port}" if url.port else ""
        auth = f"{user}:{password}@" if (user or password) else ""

        sync_url = f"{driver}://{auth}{host}{port}/postgres"

        sync_engine = create_engine(sync_url, isolation_level="AUTOCOMMIT")
        with sync_engine.connect() as conn:
            exists = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": dbname}
            ).scalar() is not None
            if not exists:
                conn.execute(text(f'CREATE DATABASE "{dbname}"'))
                logger.info("Created database %s", dbname)
    except Exception as e:
        logger.exception(f"Failed to ensure database exists for {database_url} - error: {e}")


# Ensure the target database exists before creating the async engine
ensure_database_exists(DATABASE_URL)

_debug = settings.debug
_pool_size = settings.db_pool_size
_max_overflow = settings.db_max_overflow
_pool_recycle = settings.db_pool_recycle

engine = create_async_engine(
    DATABASE_URL,
    echo=_debug,
    pool_size=_pool_size,
    max_overflow=_max_overflow,
    pool_recycle=_pool_recycle,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,
)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
