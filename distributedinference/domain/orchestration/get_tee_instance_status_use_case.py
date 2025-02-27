"""
This module provides functionality to check if a TEE instance with a given name exists.
"""

from distributedinference import api_logger
from distributedinference.domain.orchestration import get_running_tees_use_case
from distributedinference.repository.tee_orchestration_repository import (
    TeeOrchestrationRepository,
)

logger = api_logger.get()


async def execute(repository: TeeOrchestrationRepository, enclave_name: str) -> bool:
    """
    Check if a TEE instance with the given name exists among running instances.

    Args:
        repository (TeeOrchestrationRepository): Repository for TEE operations
        enclave_name (str): Name of the TEE instance to check

    Returns:
        bool: True if the TEE instance exists, False otherwise
    """
    running_tees = await get_running_tees_use_case.execute(repository)
    return any(tee.name == enclave_name for tee in running_tees)
