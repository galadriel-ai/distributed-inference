import asyncio
from uuid import UUID

from distributedinference.domain.user.entities import User
from distributedinference.repository import connection
from distributedinference.repository.user_node_repository import UserNodeRepository
from distributedinference.repository.user_repository import UserRepository
from distributedinference.service.node import create_node_service
from distributedinference.service.node.entities import CreateNodeRequest

# Modify with whatever values you wish! (check user_profile_id from user table ID column)
NODE_NAME_ALIAS = "My node"
USER_PROFILE_ID = UUID("066cc88e-e83c-7f5f-8000-8bf552a84935")


async def main():
    connection.init_defaults()
    repo = UserNodeRepository(
        connection.get_session_provider(), connection.get_session_provider_read())

    res = await create_node_service.execute(
        CreateNodeRequest(node_name=NODE_NAME_ALIAS),
        user_profile_id=USER_PROFILE_ID,
        repository=repo,
    )
    print("Created node_info:")
    print(res)


async def _insert_user(repo: UserRepository, user: User) -> User:
    await repo.insert_user(user)
    return user


async def _insert_api_key(user: User, api_key: str, repo: UserRepository) -> None:
    await repo.insert_api_key(user.uid, api_key)


asyncio.run(main())
