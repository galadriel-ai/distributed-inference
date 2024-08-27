from functools import wraps
from typing import Awaitable
from typing import Callable
from typing import Dict
from typing import Optional

import sqlalchemy
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine

import settings

connection_write = {}
connection_read = {}

DEFAULT_POOL_SIZE = 10
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
    global connection_write
    if not connection_write:
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
        connection_write = {"engine": engine, "session_maker": session_maker}


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
        session_maker = async_sessionmaker(bind=engine)
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
    session_provider = SessionProvider(is_read_only=False)
    session_provider_read = SessionProvider(is_read_only=True)


class SessionProvider:

    def __init__(self, is_read_only: bool = False):
        if is_read_only:
            self.session_maker = connection_read["session_maker"]
        else:
            self.session_maker = connection_write["session_maker"]

    def get(self) -> AsyncSession:
        return self.session_maker()


session_provider: Optional[SessionProvider] = None
session_provider_read: Optional[SessionProvider] = None


def get_session_provider() -> SessionProvider:
    if not session_provider:
        raise Exception("SessionProvider not initialized")
    return session_provider


def get_session_provider_read() -> SessionProvider:
    if not session_provider_read:
        raise Exception("SessionProvider not initialized")
    return session_provider_read


async def write(query: str, data: Dict) -> None:
    session = get_session_provider().get()
    try:
        await session.execute(sqlalchemy.text(query), data)
        await session.commit()
    finally:
        await session.close()


def read_session(func: Callable[..., Awaitable[...]]) -> Callable[..., Awaitable[...]]:
    @wraps(func)
    async def wrapper(*args, **kwargs) -> ...:
        session: AsyncSession = get_session_provider_read().get()

        kwargs["session"] = session
        try:
            result = await func(*args, **kwargs)
        finally:
            await session.close()

        return result

    return wrapper
