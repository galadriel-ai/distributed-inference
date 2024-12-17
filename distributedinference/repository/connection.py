import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine

import settings
from distributedinference.api_logger import api_logger


class DBConnection:
    def __init__(self, engine=None, session_maker=None):
        self.engine = engine
        self.session_maker = session_maker

    @classmethod
    def start_connection(cls, logger: logging.Logger, user: str, password: str, db: str, host: str, port: int,
                         pool_size: int = 100, pool_overflow: int = 0, pool_timeout: int = 1):
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
            return cls(engine=engine, session_maker=session_maker)
        except Exception as e:
            logger.error(f"Failed to create engine and session maker for user {user} and db {db}: {e}")
            raise

    def get(self) -> AsyncSession:
        if not self.session_maker:
            raise Exception("Session provider not initialized")
        return self.session_maker()


# Singleton for read-write connections, shared across the application
db_connection = DBConnection.start_connection(logger=api_logger.get(), user=settings.DB_USER,
                                              password=settings.DB_PASSWORD,
                                              db=settings.DB_DATABASE, host=settings.DB_HOST, port=settings.DB_PORT)
# Singleton for read-only connections, shared across the application
db_connection_read = DBConnection.start_connection(logger=api_logger.get(), user=settings.DB_USER_READ,
                                                   password=settings.DB_PASSWORD_READ,
                                                   db=settings.DB_DATABASE_READ, host=settings.DB_HOST_READ,
                                                   port=settings.DB_PORT_READ)
