from typing import Optional
from uuid import UUID

import sqlalchemy
from uuid_extensions import uuid7

from distributedinference.domain.user.entities import User
from distributedinference.repository.connection import SessionProvider
from distributedinference.repository.utils import utcnow

SQL_INSERT = """
INSERT INTO user_profile (
    id,
    name,
    email,
    authentication_id,
    is_password_set,
    created_at,
    last_updated_at
)
VALUES (
    :id,
    :name,
    :email,
    :authentication_id,
    false,
    :created_at,
    :last_updated_at
);
"""

SQL_UPDATE_IS_PASSWORD_SET = """
UPDATE user_profile 
SET is_password_set = :is_password_set, last_updated_at = :last_updated_at
WHERE authentication_id = :authentication_id; 
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
    up.created_at,
    up.last_updated_at
FROM user_profile up
LEFT JOIN api_key ak on up.id = ak.user_profile_id
WHERE ak.api_key = :api_key;
"""

SQL_GET_BY_EMAIL = """
SELECT
    up.id,
    up.name,
    up.email,
    up.authentication_id,
    up.created_at,
    up.last_updated_at
FROM user_profile up
WHERE lower(up.email) = lower(:email);
"""

SQL_GET_BY_AUTHENTICATION_ID = """
SELECT
    up.id,
    up.name,
    up.email,
    up.authentication_id,
    up.created_at,
    up.last_updated_at
FROM user_profile up
WHERE up.authentication_id = :authentication_id;
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

    async def update_user_password_by_authentication_id(
        self,
        authentication_id: str,
        is_password_set: bool,
    ):
        data = {
            "authentication_id": authentication_id,
            "is_password_set": is_password_set,
            "last_updated_at": utcnow(),
        }
        async with self._session_provider.get() as session:
            await session.execute(sqlalchemy.text(SQL_UPDATE_IS_PASSWORD_SET), data)
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
                    authentication_id=row.authentication_id,
                )
        return None

    async def get_user_by_email(self, email: str) -> Optional[User]:
        data = {"email": email}
        async with self._session_provider.get() as session:
            result = await session.execute(sqlalchemy.text(SQL_GET_BY_EMAIL), data)
            row = result.first()
            if row:
                return User(
                    uid=row.id,
                    name=row.name,
                    email=row.email,
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
                    authentication_id=row.authentication_id,
                )
        return None
