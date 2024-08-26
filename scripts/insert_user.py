import asyncio

from uuid_extensions import uuid7

from distributedinference.domain.user.entities import User
from distributedinference.repository import connection
from distributedinference.repository.user_repository import UserRepository


async def main():
    connection.init_defaults()
    repo = UserRepository()
    user = await _insert(repo)
    api_key = "asdasd-asd123"
    await _insert_api_key(user, api_key, repo)
    read_repo = UserRepository()
    inserted_user = await read_repo.get_user_by_api_key(api_key)
    print("User inserted")
    print(inserted_user)
    print("API key")
    print(api_key)


async def _insert(repo: UserRepository) -> User:
    user = User(
        uid=uuid7(),
        name="mock name",
        email="mock@example.com",
    )
    await repo.insert_user(user)
    return user


async def _insert_api_key(user: User, api_key: str, repo: UserRepository) -> None:
    await repo.insert_api_key(user.uid, api_key)


asyncio.run(main())
