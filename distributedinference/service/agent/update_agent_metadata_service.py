from uuid import UUID

from distributedinference.domain.agent import get_agent_use_case
from distributedinference.domain.agent import update_agent_metadata_use_case
from distributedinference.domain.agent.entities import UpdateAgentMetadataInput
from distributedinference.domain.user.entities import User
from distributedinference.repository.agent_repository import AgentRepository
from distributedinference.service import error_responses
from distributedinference.service.agent.entities import UpdateAgentMetadataRequest
from distributedinference.service.agent.entities import UpdateAgentResponse


async def execute(
    request: UpdateAgentMetadataRequest,
    agent_id: UUID,
    user: User,
    repository: AgentRepository,
) -> UpdateAgentResponse:
    agent = await get_agent_use_case.execute(repository, agent_id)
    if agent is None or agent.user_profile_id != user.uid:
        raise error_responses.NotFoundAPIError("Agent not found")

    metadata_input = UpdateAgentMetadataInput(
        description=request.description,
        client_url=request.client_url,
    )
    await update_agent_metadata_use_case.execute(agent_id, metadata_input, repository)
    return UpdateAgentResponse()
