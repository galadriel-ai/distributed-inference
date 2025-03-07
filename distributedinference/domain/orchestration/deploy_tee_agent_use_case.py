from uuid_extensions import uuid7
from typing import Any
from typing import Dict

from distributedinference.domain.agent.entities import Agent
from distributedinference.domain.orchestration.entities import TEE
from distributedinference.repository.agent_repository import AgentRepository
from distributedinference.repository.aws_storage_repository import AWSStorageRepository
from distributedinference.repository.tee_orchestration_repository import (
    TeeOrchestrationRepository,
)


async def execute(
    repository: TeeOrchestrationRepository,
    agent_repository: AgentRepository,
    aws_storage_repository: AWSStorageRepository,
    agent: Agent,
) -> TEE:
    agent_instance = await agent_repository.get_agent_instance(agent.id)
    if agent_instance:
        raise ValueError(f"Agent with id {agent.id} already has a TEE instance")

    env_vars = agent.env_vars.copy()
    agent_instance_id = uuid7()

    instance_env_vars: Dict[str, Any] = {}
    instance_env_vars["AGENT_ID"] = str(agent.id)
    instance_env_vars["AGENT_INSTANCE_ID"] = str(agent_instance_id)

    # Create user and bucket access for the agent
    aws_user_credentials = await aws_storage_repository.create_user_and_bucket_access(
        str(agent_instance_id)
    )
    if aws_user_credentials is None:
        raise ValueError(
            f"Failed to create user and bucket access for agent {agent.id}"
        )
    instance_env_vars.update(aws_user_credentials)
    env_vars.update(instance_env_vars)
    try:
        tee = await repository.create_tee(
            tee_name=str(agent_instance_id),
            docker_hub_image=agent.docker_image,
            env_vars=env_vars,
        )
        await agent_repository.insert_agent_instance(
            agent_id=agent.id,
            agent_instance_id=agent_instance_id,
            tee_host_base_url=tee.host_base_url,
            enclave_cid=tee.cid,
            instance_env_vars=instance_env_vars,
        )
        return tee
    except Exception as e:
        await aws_storage_repository.cleanup_user_and_bucket_access(
            str(agent_instance_id)
        )
        raise ValueError(f"Failed to deploy TEE for agent {agent.id}: {e}")
