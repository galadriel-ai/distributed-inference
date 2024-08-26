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

    async def insert_user(
        self,
        user: User,
    ):
        data = {
            "id": user.uid,
            "name": user.name,
            "email": user.email,
            "api_key": user.api_key,
            "created_at": utcnow(),
            "last_updated_at": utcnow(),
        }
        await connection.write(SQL_INSERT, data)
