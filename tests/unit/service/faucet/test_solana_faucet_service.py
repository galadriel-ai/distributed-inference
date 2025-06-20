from unittest.mock import AsyncMock, patch
from uuid import UUID
from datetime import datetime, timezone

import pytest

from distributedinference.domain.faucet.entities import FaucetResponse, FaucetRequest
from distributedinference.repository.blockchain_proof_repository import (
    BlockchainProofRepository,
)
from distributedinference.repository.faucet_repository import (
    FaucetRepository,
)
from distributedinference.service.faucet import solana_faucet_service
from distributedinference.service.faucet.entities import (
    SolanaFaucetRequestModel,
    SolanaFaucetResponseModel,
)


@pytest.fixture
def solana_address():
    return "4kbGbZtfkfkRVGunkbKX4M7dGPm9MghJZodjbnRZbmug"


@pytest.fixture
def request_model(solana_address):
    return SolanaFaucetRequestModel(address=solana_address)


@pytest.fixture
def mock_repository():
    return AsyncMock(spec=FaucetRepository)


@pytest.fixture
def mock_blockchain_repository():
    return AsyncMock(spec=BlockchainProofRepository)


@pytest.fixture
def mock_use_case_response():
    return FaucetResponse(
        success=True,
        transaction_signature="4B6YNfEAC6rysjKKcF7iiWEoRfUGvwvKEhQLkM35rpj1CmD7RoydkUHDL4tVmqXyXLoQTAyXEd2WCqxW2SVkgCeS",
        message="Successfully sent 0.0001 SOL",
    )


@patch("distributedinference.domain.faucet.solana_faucet_use_case.execute")
async def test_execute_success(
    mock_execute,
    request_model,
    mock_repository,
    mock_blockchain_repository,
    mock_use_case_response,
):
    # Setup
    mock_execute.return_value = mock_use_case_response

    # Execute
    result = await solana_faucet_service.execute(
        request_model, mock_repository, mock_blockchain_repository
    )

    # Assert
    assert result is mock_use_case_response

    # Verify use case was called with correct parameters
    mock_execute.assert_called_once_with(
        request_model.address,
        mock_repository,
        mock_blockchain_repository,
    )


@patch("distributedinference.domain.faucet.solana_faucet_use_case.execute")
async def test_execute_error_propagation(
    mock_execute,
    request_model,
    mock_repository,
    mock_blockchain_repository,
):
    # Setup - make the use case raise an exception
    test_error = ValueError("Test error")
    mock_execute.side_effect = test_error

    # Execute and assert exception is propagated
    with pytest.raises(ValueError) as exc_info:
        await solana_faucet_service.execute(
            request_model, mock_repository, mock_blockchain_repository
        )

    assert exc_info.value is test_error
