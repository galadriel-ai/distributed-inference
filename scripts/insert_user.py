import asyncio

from uuid_extensions import uuid7

from distributedinference.domain.user.entities import User
from distributedinference.repository import connection
from distributedinference.repository.user_repository import UserRepository


async def main():
    connection.init_defaults()
    repo = UserRepository()
    await _insert(repo)


async def _insert(repo: UserRepository):
    await repo.insert_user(User(
        uid=uuid7(),
        name="mock name",
        email="mock@example.com",
        api_key="api-key-123",
    ))


asyncio.run(main())
