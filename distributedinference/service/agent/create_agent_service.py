from distributedinference.domain.orchestration import exceptions
from distributedinference.domain.user.entities import User
from distributedinference.domain.agent import create_agent_use_case
from distributedinference.domain.agent.entities import CreateAgentInput
from distributedinference.domain.orchestration import deploy_tee_agent_use_case
from distributedinference.repository.agent_repository import AgentRepository
from distributedinference.repository.aws_storage_repository import AWSStorageRepository
from distributedinference.repository.tee_orchestration_repository import (
    TeeOrchestrationRepository,
)
from distributedinference.service import error_responses
from distributedinference.service.agent.entities import CreateAgentRequest
from distributedinference.service.agent.entities import CreateAgentResponse


async def execute(
    repository: AgentRepository,
    tee_orchestration_repository: TeeOrchestrationRepository,
    aws_storage_repository: AWSStorageRepository,
    user: User,
    request: CreateAgentRequest,
) -> CreateAgentResponse:
    input = CreateAgentInput(
        user_id=user.uid,
        name=request.name,
        docker_image=request.docker_image,
        docker_image_hash=request.docker_image_hash,
        env_vars=request.env_vars,
    )
    output = await create_agent_use_case.execute(repository, input)

    # launch the agent in a TEE
    try:
        aws_user_credentials = (
            await aws_storage_repository.create_user_and_bucket_access(
                str(output.agent.id)
            )
        )
        if aws_user_credentials is None:
            raise ValueError(
                f"Failed to create user and bucket access for agent {output.agent.id}"
            )
        await deploy_tee_agent_use_case.execute(
            user,
            tee_orchestration_repository,
            repository,
            aws_user_credentials,
            output.agent,
        )
    except exceptions.NoCapacityError:
        await aws_storage_repository.cleanup_user_and_bucket_access(
            str(output.agent.id)
        )
        raise error_responses.NoCapacityError()
    except Exception as e:
        await aws_storage_repository.cleanup_user_and_bucket_access(
            str(output.agent.id)
        )
        raise e
    return CreateAgentResponse(agent_id=output.agent.id)
