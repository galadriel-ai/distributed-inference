from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine

import settings
from distributedinference import api_logger

connection = {}
connection_read = {}

DEFAULT_POOL_SIZE = 100
DEFAULT_POOL_OVERFLOW = 0
DEFAULT_POOL_TIMEOUT = 1

logger = api_logger.get()


# pylint: disable=R0913
# pylint: disable=W0603
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
        logger.info("connection.py - creating new engine and session maker")
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
        session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)
        connection = {"engine": engine, "session_maker": session_maker}


def init_read(
    user,
    password,
    db,
    host="localhost",
    port=5432,
    pool_size=DEFAULT_POOL_SIZE,
    pool_overflow=DEFAULT_POOL_OVERFLOW,
    pool_timeout=DEFAULT_POOL_TIMEOUT,
):
    global connection_read
    if not connection_read:
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
        session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)
        connection_read = {"engine": engine, "session_maker": session_maker}


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
    init_read(
        user=settings.DB_USER_READ,
        password=settings.DB_PASSWORD_READ,
        db=settings.DB_DATABASE_READ,
        host=settings.DB_HOST_READ,
        port=settings.DB_PORT_READ,
        pool_size=pool_size,
        pool_overflow=pool_overflow,
        pool_timeout=pool_timeout,
    )
    global session_provider
    global session_provider_read
    session_provider = SessionProvider(connection)
    session_provider_read = SessionProvider(connection_read)


class SessionProvider:

    def __init__(self, _connection):
        self.session_maker = _connection["session_maker"]

    def get(self) -> AsyncSession:
        return self.session_maker()


session_provider: Optional[SessionProvider] = None
session_provider_read: Optional[SessionProvider] = None


def get_session_provider() -> SessionProvider:
    if not session_provider:
        # pylint: disable=W0719
        raise Exception("SessionProvider not initialized")
    return session_provider


def get_session_provider_read() -> SessionProvider:
    if not session_provider_read:
        # pylint: disable=W0719
        raise Exception("SessionProviderRead not initialized")
    return session_provider_read
