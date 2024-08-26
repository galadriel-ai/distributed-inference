import sqlalchemy
from sqlalchemy.ext.asyncio import AsyncSession

from distributedinference.domain.user.entities import User
from distributedinference.repository import connection
from distributedinference.repository.utils import utcnow

SQL_INSERT = """
INSERT INTO user_profile (
    id,
    name,
    email,
    api_key,
    created_at,
    last_updated_at
)
VALUES (
    :id,
    :name,
    :email,
    :api_key,
    :created_at,
    :last_updated_at
);
"""


class UserRepository:
    @connection.session
    async def insert_user(
        self,
        user: User,
        session: AsyncSession
    ):
        data = {
            "id": user.uid,
            "name": user.name,
            "email": user.email,
            "api_key": user.api_key,
            "created_at": utcnow(),
            "last_updated_at": utcnow(),
        }
        await session.execute(sqlalchemy.text(SQL_INSERT), data)
