import json
from typing import List
from typing import Optional
from uuid import UUID

import sqlalchemy
from uuid_extensions import uuid7

from distributedinference import api_logger
from distributedinference.domain.user.entities import ApiKey
from distributedinference.domain.user.entities import User
from distributedinference.repository.connection import SessionProvider
from distributedinference.repository.utils import utcnow
from distributedinference.utils.timer import async_timer

SQL_INSERT = """
INSERT INTO user_profile (
    id,
    name,
    username,
    email,
    authentication_id,
    is_password_set,
    created_at,
    last_updated_at
)
VALUES (
    :id,
    :name,
    :username,
    :email,
    :authentication_id,
    :is_password_set,
    :created_at,
    :last_updated_at
);
"""

SQL_UPDATE_USERNAME_AND_IS_PASSWORD_SET = """
UPDATE 
    user_profile 
SET 
    is_password_set = :is_password_set,
    username = :username,
    last_updated_at = :last_updated_at
WHERE authentication_id = :authentication_id; 
"""

SQL_UPDATE_USER_PROFILE_DATA = """
UPDATE 
    user_profile 
SET 
    profile_data = :profile_data,
    last_updated_at = :last_updated_at
WHERE id = :user_profile_id; 
"""

SQL_INSERT_API_KEY = """
INSERT INTO api_key (
    id,
    user_profile_id,
    api_key,
    created_at,
    last_updated_at
)
VALUES (
    :id,
    :user_profile_id,
    :api_key,
    :created_at,
    :last_updated_at
);
"""

SQL_GET_BY_API_KEY = """
SELECT
    up.id,
    up.name,
    up.email,
    up.authentication_id,
    up.profile_data,
    up.usage_tier_id,
    up.created_at,
    up.last_updated_at
FROM user_profile up
LEFT JOIN api_key ak on up.id = ak.user_profile_id
WHERE 
    ak.api_key = :api_key
    AND ak.is_deleted IS FALSE;
"""

SQL_GET_BY_USERNAME = """
SELECT
    id,
    name,
    username,
    email,
    profile_data,
    usage_tier_id,
    authentication_id,
    created_at,
    last_updated_at
FROM user_profile
WHERE username ILIKE :username;
"""

SQL_GET_BY_AUTHENTICATION_ID = """
SELECT
    up.id,
    up.name,
    up.email,
    up.authentication_id,
    up.profile_data,
    up.usage_tier_id,
    up.created_at,
    up.last_updated_at
FROM user_profile up
WHERE up.authentication_id = :authentication_id;
"""

SQL_GET_BY_EMAIL = """
SELECT
    up.id,
    up.name,
    up.email,
    up.authentication_id,
    up.profile_data,
    up.usage_tier_id,
    up.created_at,
    up.last_updated_at
FROM user_profile up
WHERE up.email ILIKE :email;
"""

SQL_GET_USER_API_KEYS = """
SELECT
    id,
    api_key,
    created_at
FROM api_key
WHERE user_profile_id = :user_profile_id AND is_deleted = false;
"""

SQL_DELETE_USER_API_KEY = """
UPDATE api_key
SET is_deleted = true
WHERE user_profile_id = :user_profile_id AND id = :api_key_id;
"""


logger = api_logger.get()


class UserRepository:

    def __init__(
        self, session_provider: SessionProvider, session_provider_read: SessionProvider
    ):
        self._session_provider = session_provider
        self._session_provider_read = session_provider_read

    @async_timer("user_repository.insert_user", logger=logger)
    async def insert_user(
        self,
        user: User,
        is_password_set: bool = False,
    ):
        data = {
            "id": user.uid,
            "name": user.name,
            "username": user.username,
            "email": user.email,
            "authentication_id": user.authentication_id,
            "is_password_set": is_password_set,
            "created_at": utcnow(),
            "last_updated_at": utcnow(),
        }
        async with self._session_provider.get() as session:
            await session.execute(sqlalchemy.text(SQL_INSERT), data)
            await session.commit()

    @async_timer(
        "user_repository.update_user_username_and_password_by_authentication_id",
        logger=logger,
    )
    async def update_user_username_and_password_by_authentication_id(
        self,
        authentication_id: str,
        username: str,
        is_password_set: bool,
    ):
        data = {
            "authentication_id": authentication_id,
            "username": username,
            "is_password_set": is_password_set,
            "last_updated_at": utcnow(),
        }
        async with self._session_provider.get() as session:
            await session.execute(
                sqlalchemy.text(SQL_UPDATE_USERNAME_AND_IS_PASSWORD_SET), data
            )
            await session.commit()

    @async_timer("user_repository.update_user_profile_data", logger=logger)
    async def update_user_profile_data(
        self,
        user_profile_id: UUID,
        profile_data: dict,
    ):
        data = {
            "user_profile_id": user_profile_id,
            "profile_data": json.dumps(profile_data),
            "last_updated_at": utcnow(),
        }
        async with self._session_provider.get() as session:
            await session.execute(sqlalchemy.text(SQL_UPDATE_USER_PROFILE_DATA), data)
            await session.commit()

    @async_timer("user_repository.insert_api_key", logger=logger)
    async def insert_api_key(self, user_id: UUID, api_key: str) -> UUID:
        api_key_id = uuid7()
        data = {
            "id": api_key_id,
            "user_profile_id": user_id,
            "api_key": api_key,
            "created_at": utcnow(),
            "last_updated_at": utcnow(),
        }
        async with self._session_provider.get() as session:
            await session.execute(sqlalchemy.text(SQL_INSERT_API_KEY), data)
            await session.commit()
        return api_key_id

    @async_timer("user_repository.get_user_by_api_key", logger=logger)
    async def get_user_by_api_key(self, api_key: str) -> Optional[User]:
        data = {"api_key": api_key}
        async with self._session_provider_read.get() as session:
            result = await session.execute(sqlalchemy.text(SQL_GET_BY_API_KEY), data)
            row = result.first()
            if row:
                return User(
                    uid=row.id,
                    name=row.name,
                    email=row.email,
                    usage_tier_id=row.usage_tier_id,
                    profile_data=row.profile_data,
                    authentication_id=row.authentication_id,
                )
        return None

    @async_timer("user_repository.get_user_by_username", logger=logger)
    async def get_user_by_username(self, username: str) -> Optional[User]:
        data = {"username": username}
        async with self._session_provider_read.get() as session:
            result = await session.execute(sqlalchemy.text(SQL_GET_BY_USERNAME), data)
            row = result.first()
            if row:
                return User(
                    uid=row.id,
                    name=row.name,
                    username=row.username,
                    email=row.email,
                    usage_tier_id=row.usage_tier_id,
                    profile_data=row.profile_data,
                    authentication_id=row.authentication_id,
                )
        return None

    @async_timer("user_repository.get_user_by_authentication_id", logger=logger)
    async def get_user_by_authentication_id(
        self, authentication_id: str
    ) -> Optional[User]:
        data = {"authentication_id": authentication_id}
        async with self._session_provider_read.get() as session:
            result = await session.execute(
                sqlalchemy.text(SQL_GET_BY_AUTHENTICATION_ID), data
            )
            row = result.first()
            if row:
                return User(
                    uid=row.id,
                    name=row.name,
                    email=row.email,
                    usage_tier_id=row.usage_tier_id,
                    profile_data=row.profile_data,
                    authentication_id=row.authentication_id,
                )
        return None

    @async_timer("user_repository.get_user_by_email", logger=logger)
    async def get_user_by_email(self, email: str) -> Optional[User]:
        data = {"email": email.strip()}
        async with self._session_provider_read.get() as session:
            result = await session.execute(sqlalchemy.text(SQL_GET_BY_EMAIL), data)
            row = result.first()
            if row:
                return User(
                    uid=row.id,
                    name=row.name,
                    email=row.email,
                    usage_tier_id=row.usage_tier_id,
                    profile_data=row.profile_data,
                    authentication_id=row.authentication_id,
                )
        return None

    @async_timer("user_repository.get_user_api_keys", logger=logger)
    async def get_user_api_keys(self, user_profile_id: UUID) -> List[ApiKey]:
        data = {"user_profile_id": user_profile_id}
        api_keys = []
        async with self._session_provider_read.get() as session:
            rows = await session.execute(sqlalchemy.text(SQL_GET_USER_API_KEYS), data)
            for row in rows:
                api_keys.append(
                    ApiKey(
                        uid=row.id,
                        api_key=row.api_key,
                        created_at=row.created_at,
                    )
                )
        return api_keys

    @async_timer("user_repository.delete_api_key", logger=logger)
    async def delete_api_key(self, user_profile_id: UUID, api_key_id: UUID) -> None:
        data = {"user_profile_id": user_profile_id, "api_key_id": api_key_id}
        async with self._session_provider.get() as session:
            await session.execute(sqlalchemy.text(SQL_DELETE_USER_API_KEY), data)
            await session.commit()


if __name__ == "__main__":
    import asyncio
    from distributedinference.repository import connection

    async def main():
        connection.init_defaults()
        user_repository = UserRepository(
            connection.get_session_provider(), connection.get_session_provider_read()
        )
        user = await user_repository.get_user_by_username("dino")
        print(user.profile_data is None)

    asyncio.run(main())
