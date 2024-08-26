from typing import Optional
from uuid import UUID

import sqlalchemy
from sqlalchemy.ext.asyncio import AsyncSession
from uuid_extensions import uuid7

from distributedinference.domain.user.entities import User
from distributedinference.repository import connection
from distributedinference.repository.utils import utcnow

SQL_INSERT = """
INSERT INTO user_profile (
    id,
    name,
    email,
    created_at,
    last_updated_at
)
VALUES (
    :id,
    :name,
    :email,
    :created_at,
    :last_updated_at
);
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
    up.created_at,
    up.last_updated_at
FROM user_profile up
LEFT JOIN api_key ak on up.id = ak.user_profile_id
WHERE ak.api_key = :api_key;
"""


class UserRepository:

    async def insert_user(
        self,
        user: User,
    ):
        data = {
            "id": user.uid,
            "name": user.name,
            "email": user.email,
            "created_at": utcnow(),
            "last_updated_at": utcnow(),
        }
        await connection.write(SQL_INSERT, data)

    async def insert_api_key(
        self,
        user_id: UUID,
        api_key: str
    ) -> UUID:
        api_key_id = uuid7()
        data = {
            "id": api_key_id,
            "user_profile_id": user_id,
            "api_key": api_key,
            "created_at": utcnow(),
            "last_updated_at": utcnow(),
        }
        await connection.write(SQL_INSERT_API_KEY, data)
        return api_key_id

    @connection.read_session
    async def get_user_by_api_key(self, api_key: str, session: AsyncSession) -> Optional[User]:
        data = {
            "api_key": api_key
        }
        rows = await session.execute(sqlalchemy.text(SQL_GET_BY_API_KEY), data)
        for row in rows:
            return User(
                uid=row.id,
                name=row.name,
                email=row.email,
            )
        return None
