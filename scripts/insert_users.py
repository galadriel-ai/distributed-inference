import asyncio

from uuid_extensions import uuid7

from distributedinference.domain.user.entities import User
from distributedinference.repository import connection
from distributedinference.repository.user_repository import UserRepository

USERS = [
    (
        "gpu-api-key",
        User(
            uid=uuid7(),
            name="gpu user",
            email="gpu@user.com",
        ),
    ),
    (
        "consumer-api-key",
        User(
            uid=uuid7(),
            name="consumer user",
            email="consumer@user.com",
        ),
    ),
]


async def main():
    connection.init_defaults()
    repo = UserRepository(connection.get_session_provider())

    print(f"Inserting {len(USERS)} users.")
    for api_key, user in USERS:
        user = await _insert_user(repo, user)
        await _insert_api_key(user, api_key, repo)
        read_repo = UserRepository(connection.get_session_provider())
        inserted_user = await read_repo.get_user_by_api_key(api_key)
        print(f"  Inserted user {inserted_user} with api_key='{api_key}'")


async def _insert_user(repo: UserRepository, user: User) -> User:
    await repo.insert_user(user)
    return user


async def _insert_api_key(user: User, api_key: str, repo: UserRepository) -> None:
    await repo.insert_api_key(user.uid, api_key)


asyncio.run(main())
