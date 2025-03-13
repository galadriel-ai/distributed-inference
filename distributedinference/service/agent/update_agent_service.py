from uuid import UUID

from typing import Any
from typing import Dict
from typing import List

from distributedinference import api_logger
from distributedinference.domain.user.entities import User
from distributedinference.domain.agent import get_agent_use_case
from distributedinference.domain.agent import update_agent_use_case
from distributedinference.domain.agent.entities import UpdateAgentInput
from distributedinference.domain.orchestration import deploy_tee_agent_use_case
from distributedinference.domain.orchestration import exceptions
from distributedinference.domain.orchestration import stop_agent_tee_use_case
from distributedinference.repository.agent_repository import AgentRepository
from distributedinference.repository.tee_orchestration_repository import (
    TeeOrchestrationRepository,
)
from distributedinference.service import error_responses
from distributedinference.service.agent.entities import UpdateAgentRequest
from distributedinference.service.agent.entities import UpdateAgentResponse

logger = api_logger.get()


async def execute(
    repository: AgentRepository,
    tee_orchestration_repository: TeeOrchestrationRepository,
    user: User,
    agent_id: UUID,
    request: UpdateAgentRequest,
) -> UpdateAgentResponse:
    # Verify agent exists and belongs to user
    agent = await get_agent_use_case.execute(repository, agent_id)
    if not agent or agent.user_profile_id != user.uid:
        raise error_responses.NotFoundAPIError("Agent not found")

    # Create update input
    input = UpdateAgentInput(
        agent_id=agent_id,
        name=request.name,
        docker_image=request.docker_image,
        docker_image_hash=request.docker_image_hash,
        env_vars=request.env_vars,
    )

    # Get agent instance
    agent_instance = await repository.get_agent_instance(agent_id)

    if agent_instance:
        # Stop running agent instance
        await stop_agent_tee_use_case.execute(
            tee_orchestration_repository,
            repository,
            agent,
        )
    else:
        # Try to find a previously stopped instance
        logger.warning(
            f"No running agent instance found for agent {agent_id}, getting newest stopped agent instance"
        )
        agent_instances = await repository.get_agent_instances()
        if not agent_instances:
            raise error_responses.NotFoundAPIError(
                "Cannot update agent that has never been deployed"
            )
        agent_instance = agent_instances[0]

    # Extract AWS credentials
    aws_user_credentials = {
        "AWS_ACCESS_KEY_ID": agent_instance.instance_env_vars.get("AWS_ACCESS_KEY_ID"),
        "AWS_SECRET_ACCESS_KEY": agent_instance.instance_env_vars.get(
            "AWS_SECRET_ACCESS_KEY"
        ),
    }

    # Update agent
    await update_agent_use_case.execute(repository, input)

    # Deploy agent
    try:
        await deploy_tee_agent_use_case.execute(
            user,
            tee_orchestration_repository,
            repository,
            aws_user_credentials,
            agent,
        )
    except exceptions.NoCapacityError:
        raise error_responses.NoCapacityError()
    except Exception as e:
        raise error_responses.InternalServerAPIError(str(e))

    return UpdateAgentResponse()
