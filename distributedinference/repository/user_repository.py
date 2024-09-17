import json
from typing import List
from typing import Optional
from uuid import UUID

import sqlalchemy
from uuid_extensions import uuid7

from distributedinference.domain.user.entities import ApiKey
from distributedinference.domain.user.entities import User
from distributedinference.repository.connection import SessionProvider
from distributedinference.repository.utils import utcnow

SQL_INSERT = """
INSERT INTO user_profile (
    id,
    name,
    email,
    authentication_id,
    created_at,
    last_updated_at
)
VALUES (
    :id,
    :name,
    :email,
    :authentication_id,
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
    up.created_at,
    up.last_updated_at
FROM user_profile up
LEFT JOIN api_key ak on up.id = ak.user_profile_id
WHERE ak.api_key = :api_key;
"""

SQL_GET_BY_USERNAME = """
SELECT
    id,
    name,
    username,
    email,
    profile_data,
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
    up.created_at,
    up.last_updated_at
FROM user_profile up
WHERE up.authentication_id = :authentication_id;
"""

SQL_GET_USER_API_KEYS = """
SELECT
    api_key,
    created_at
FROM api_key
WHERE user_profile_id = :user_profile_id;
"""


class UserRepository:

    def __init__(self, session_provider: SessionProvider):
        self._session_provider = session_provider

    async def insert_user(
        self,
        user: User,
    ):
        data = {
            "id": user.uid,
            "name": user.name,
            "email": user.email,
            "authentication_id": user.authentication_id,
            "created_at": utcnow(),
            "last_updated_at": utcnow(),
        }
        async with self._session_provider.get() as session:
            await session.execute(sqlalchemy.text(SQL_INSERT), data)
            await session.commit()

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

    async def get_user_by_api_key(self, api_key: str) -> Optional[User]:
        data = {"api_key": api_key}
        async with self._session_provider.get() as session:
            result = await session.execute(sqlalchemy.text(SQL_GET_BY_API_KEY), data)
            row = result.first()
            if row:
                return User(
                    uid=row.id,
                    name=row.name,
                    email=row.email,
                    profile_data=row.profile_data,
                    authentication_id=row.authentication_id,
                )
        return None

    async def get_user_by_username(self, username: str) -> Optional[User]:
        data = {"username": username}
        async with self._session_provider.get() as session:
            result = await session.execute(sqlalchemy.text(SQL_GET_BY_USERNAME), data)
            row = result.first()
            if row:
                return User(
                    uid=row.id,
                    name=row.name,
                    username=row.username,
                    email=row.email,
                    profile_data=row.profile_data,
                    authentication_id=row.authentication_id,
                )
        return None

    async def get_user_by_authentication_id(
        self, authentication_id: str
    ) -> Optional[User]:
        data = {"authentication_id": authentication_id}
        async with self._session_provider.get() as session:
            result = await session.execute(
                sqlalchemy.text(SQL_GET_BY_AUTHENTICATION_ID), data
            )
            row = result.first()
            if row:
                return User(
                    uid=row.id,
                    name=row.name,
                    email=row.email,
                    profile_data=row.profile_data,
                    authentication_id=row.authentication_id,
                )
        return None

    async def get_user_api_keys(self, user_profile_id: UUID) -> List[ApiKey]:
        data = {"user_profile_id": user_profile_id}
        api_keys = []
        async with self._session_provider.get() as session:
            rows = await session.execute(sqlalchemy.text(SQL_GET_USER_API_KEYS), data)
            for row in rows:
                api_keys.append(ApiKey(api_key=row.api_key, created_at=row.created_at))
        return api_keys


if __name__ == "__main__":
    import asyncio
    from distributedinference.repository import connection

    async def main():
        connection.init_defaults()
        user_repository = UserRepository(connection.get_session_provider())
        user = await user_repository.get_user_by_username("dino")
        print(user.profile_data is None)

    asyncio.run(main())
