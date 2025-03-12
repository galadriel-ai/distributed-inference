from typing import List
from uuid import UUID

from distributedinference.domain.agent import get_dashboard_details_use_case
from distributedinference.domain.agent.entities import ExplorerAgentInstance
from distributedinference.repository.agent_explorer_repository import (
    AgentExplorerRepository,
)
from distributedinference.service.agent_explorer.entities import AgentDetailsResponse
from distributedinference.service.agent_explorer.entities import AgentInstanceModel


async def execute(
    agent_id: UUID,
    agent_repository: AgentExplorerRepository,
) -> AgentDetailsResponse:
    agent = await get_dashboard_details_use_case.execute(agent_id, agent_repository)
    return AgentDetailsResponse(
        agent_id=agent.id,
        name=agent.name,
        docker_image=agent.docker_image,
        created_at=int(agent.created_at.timestamp()),
        agent_instances=_map_agent_instances(agent.agent_instances),
    )


def _map_agent_instances(
    agent_instances: List[ExplorerAgentInstance],
) -> List[AgentInstanceModel]:
    return [
        AgentInstanceModel(
            enclave_cid=i.enclave_cid,
            is_deleted=i.is_deleted,
            pcr0=i.pcr0,
            attestation=i.attestation,
            created_at=int(i.created_at.timestamp()),
        )
        for i in agent_instances
    ]
