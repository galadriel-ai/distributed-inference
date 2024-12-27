import logging
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
    AsyncEngine,
)

import settings
from distributedinference import api_logger

DEFAULT_POOL_SIZE = 100
DEFAULT_POOL_OVERFLOW = 0
DEFAULT_POOL_TIMEOUT = 1


class SessionProvider:
    def __init__(
        self,
        engine: AsyncEngine = None,
        session_maker: async_sessionmaker = None,
        logger: logging.Logger = None,
    ):
        self.engine = engine
        self.session_maker = session_maker
        self.logger = logger

    @classmethod
    def start_connection(  # pylint: disable=too-many-arguments
        cls,
        logger: logging.Logger,
        user: str,
        password: str,
        db: str,
        host: str,
        port: int,
        pool_size: int = DEFAULT_POOL_SIZE,
        pool_overflow: int = DEFAULT_POOL_OVERFLOW,
        pool_timeout: int = DEFAULT_POOL_TIMEOUT,
    ) -> "SessionProvider":
        logger.info("connection.py - creating new engine and session maker")
        url = f"postgresql+psycopg_async://{user}:{password}@{host}:{port}/{db}"

        try:
            engine = create_async_engine(
                url,
                max_overflow=pool_overflow,
                pool_timeout=pool_timeout,
                pool_size=pool_size,
                pool_recycle=1800,
            )
            session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)
            return cls(engine=engine, session_maker=session_maker, logger=logger)
        except Exception as e:
            logger.error(
                f"Failed to create engine and session maker for user {user} and db {db}: {e}"
            )
            raise

    def get(self) -> AsyncSession:
        if not self.session_maker:
            raise Exception("Session provider not initialized")  # pylint: disable=broad-exception-raised
        return self.session_maker()


# Singleton for read-write and read-only sessions, shared across the application
db_session_provider = {
    "write": SessionProvider.start_connection(
        logger=api_logger.get(),
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        db=settings.DB_DATABASE,
        host=settings.DB_HOST,
        port=settings.DB_PORT,
    ),
    "read": SessionProvider.start_connection(
        logger=api_logger.get(),
        user=settings.DB_USER_READ,
        password=settings.DB_PASSWORD_READ,
        db=settings.DB_DATABASE_READ,
        host=settings.DB_HOST_READ,
        port=settings.DB_PORT_READ,
    ),
}
