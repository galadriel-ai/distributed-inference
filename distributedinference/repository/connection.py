from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine

import settings

connection = {}

DEFAULT_POOL_SIZE = 50
DEFAULT_POOL_OVERFLOW = 100
DEFAULT_POOL_TIMEOUT = 3


def init(
    user,
    password,
    db,
    host="localhost",
    port=5432,
    pool_size=DEFAULT_POOL_SIZE,
    pool_overflow=DEFAULT_POOL_OVERFLOW,
    pool_timeout=DEFAULT_POOL_TIMEOUT,
):
    global connection
    if not connection:
        url = "postgresql+asyncpg://{}:{}@{}:{}/{}"
        url = url.format(user, password, host, port, db)

        # The return value of create_engine() is our connection object
        engine = create_async_engine(
            url,
            max_overflow=pool_overflow,
            pool_timeout=pool_timeout,
            pool_size=pool_size,
            pool_recycle=1800,
        )
        session_maker = async_sessionmaker(bind=engine)
        connection = {"engine": engine, "session_maker": session_maker}


def init_defaults():
    _init_all(DEFAULT_POOL_SIZE, DEFAULT_POOL_OVERFLOW, DEFAULT_POOL_TIMEOUT)


def _init_all(pool_size: int, pool_overflow: int, pool_timeout: int):
    init(
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        db=settings.DB_DATABASE,
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        pool_size=pool_size,
        pool_overflow=pool_overflow,
        pool_timeout=pool_timeout,
    )
    global session_provider
    session_provider = SessionProvider()


class SessionProvider:

    def __init__(self):
        self.session_maker = connection["session_maker"]

    def get(self) -> AsyncSession:
        return self.session_maker()


session_provider: Optional[SessionProvider] = None


def get_session_provider() -> SessionProvider:
    if not session_provider:
        raise Exception("SessionProvider not initialized")
    return session_provider
