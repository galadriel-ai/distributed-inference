import asyncio
import pytest
from unittest.mock import AsyncMock, patch
from uuid import UUID

from distributedinference.repository.agent_repository import AgentRepository
from distributedinference.repository.aws_storage_repository import AWSStorageRepository
from distributedinference.repository.tee_orchestration_repository import (
    TeeOrchestrationRepository,
)
from distributedinference.domain.orchestration.jobs import monitor_tee_instances


AGENT_INSTANCE_1_ID = UUID("123e4567-e89b-12d3-a456-426614174000")
AGENT_INSTANCE_2_ID = UUID("223e4567-e89b-12d3-a456-426614174001")


@pytest.mark.asyncio
async def test_execute():
    # Mock repositories
    agent_repository = AsyncMock(spec=AgentRepository)
    tee_orchestration_repository = AsyncMock(spec=TeeOrchestrationRepository)
    aws_storage_repository = AsyncMock(spec=AWSStorageRepository)

    # Mock agent instances
    mock_agent_instance_1 = AsyncMock()
    mock_agent_instance_1.id = AGENT_INSTANCE_1_ID

    mock_agent_instance_2 = AsyncMock()
    mock_agent_instance_2.id = AGENT_INSTANCE_2_ID

    agent_repository.get_agent_instances.return_value = [
        mock_agent_instance_1,
        mock_agent_instance_2,
    ]

    # Mock running TEEs
    mock_tee_1 = AsyncMock()
    mock_tee_1.name = str(AGENT_INSTANCE_1_ID)

    mock_tee_2 = AsyncMock()
    mock_tee_2.name = "not-a-valid-uuid"  # Invalid UUID

    tee_orchestration_repository.get_all_tees.return_value = [mock_tee_1, mock_tee_2]

    # Run execute function in a controlled manner
    task = asyncio.create_task(
        monitor_tee_instances._check_agent_instances(
            agent_repository, tee_orchestration_repository, aws_storage_repository
        )
    )

    await asyncio.sleep(0.05)  # Allow execution to run briefly
    task.cancel()

    try:
        await task
    except asyncio.CancelledError:
        pass

    # Assertions
    agent_repository.get_agent_instances.assert_called()
    tee_orchestration_repository.get_all_tees.assert_called()

    # Ensure only the agent without a TEE was deleted
    agent_repository.delete_agent_instance.assert_called_once_with(
        mock_agent_instance_2.id
    )
    aws_storage_repository.cleanup_user_and_bucket_access.assert_called_once_with(
        str(mock_agent_instance_2.id)
    )
