import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID
import pytest
import settings
from decimal import Decimal

from solders.pubkey import Pubkey
from solana.constants import LAMPORTS_PER_SOL

from distributedinference.domain.faucet import solana_faucet_use_case
from distributedinference.domain.faucet.entities import SolanaFaucetRequest, SolanaFaucetResponse
from distributedinference.repository.blockchain_proof_repository import BlockchainProofRepository
from distributedinference.repository.solana_faucet_repository import SolanaFaucetRepository
from distributedinference.service import error_responses


@pytest.fixture
def user_id():
    return UUID("066e9449-c696-7462-8000-3196255ced8d")


@pytest.fixture
def solana_address():
    return "4kbGbZtfkfkRVGunkbKX4M7dGPm9MghJZodjbnRZbmug"


@pytest.fixture
def mock_repository():
    mock = AsyncMock(spec=SolanaFaucetRepository)
    mock.get_recent_request_by_user_profile_id.return_value = None
    mock.get_recent_request_by_address.return_value = None
    return mock


@pytest.fixture
def mock_blockchain_repository():
    mock = AsyncMock(spec=BlockchainProofRepository)
    mock_tx_result = MagicMock()
    mock_tx_result.value = (
        "4B6YNfEAC6rysjKKcF7iiWEoRfUGvwvKEhQLkM35rpj1CmD7RoydkUHDL4tVmqXyXLoQTAyXEd2WCqxW2SVkgCeS"
    )
    mock.transfer.return_value = mock_tx_result
    return mock


async def test_execute_success(
    user_id, solana_address, mock_repository, mock_blockchain_repository
):
    # Execute
    response = await solana_faucet_use_case.execute(
        user_id, solana_address, mock_repository, mock_blockchain_repository
    )

    # Assert
    assert isinstance(response, SolanaFaucetResponse)
    assert response.success is True
    assert (
        response.transaction_signature
        == "4B6YNfEAC6rysjKKcF7iiWEoRfUGvwvKEhQLkM35rpj1CmD7RoydkUHDL4tVmqXyXLoQTAyXEd2WCqxW2SVkgCeS"
    )
    assert f"Successfully sent {settings.SOLANA_FAUCET_AMOUNT} SOL" in response.message

    # Verify repository calls
    mock_repository.get_recent_request_by_user_profile_id.assert_called_once_with(user_id)
    mock_repository.get_recent_request_by_address.assert_called_once_with(solana_address)

    # Verify blockchain call
    mock_blockchain_repository.transfer.assert_called_once()
    args, _ = mock_blockchain_repository.transfer.call_args
    assert isinstance(args[0], Pubkey)
    assert str(args[0]) == solana_address
    # Check the amount is calculated correctly
    expected_lamports = int(Decimal(settings.SOLANA_FAUCET_AMOUNT) * LAMPORTS_PER_SOL)
    assert args[1] == expected_lamports

    # Verify request saved
    mock_repository.add_request.assert_called_once()
    request = mock_repository.add_request.call_args[0][0]
    assert isinstance(request, SolanaFaucetRequest)
    assert request.user_profile_id == user_id
    assert request.solana_address == solana_address
    assert (
        request.transaction_signature
        == "4B6YNfEAC6rysjKKcF7iiWEoRfUGvwvKEhQLkM35rpj1CmD7RoydkUHDL4tVmqXyXLoQTAyXEd2WCqxW2SVkgCeS"
    )


async def test_execute_user_rate_limit(
    user_id, solana_address, mock_repository, mock_blockchain_repository
):
    # Setup - user has a recent request
    mock_recent_request = SolanaFaucetRequest(
        id=UUID("218506ee-af34-4320-8a09-b6432dafc187"),
        user_profile_id=user_id,
        solana_address=solana_address,
        transaction_signature="some_signature",
        created_at=datetime.datetime.now(),
    )
    mock_repository.get_recent_request_by_user_profile_id.return_value = mock_recent_request

    # Execute and expect exception
    with pytest.raises(error_responses.RateLimitError) as exc_info:
        await solana_faucet_use_case.execute(
            user_id, solana_address, mock_repository, mock_blockchain_repository
        )

    # Assert error message contains rate limit info
    assert f"{settings.SOLANA_FAUCET_RATE_LIMIT_HOURS} hours" in str(exc_info.value)

    # Verify only the first repository call was made
    mock_repository.get_recent_request_by_user_profile_id.assert_called_once()
    mock_repository.get_recent_request_by_address.assert_not_called()
    mock_blockchain_repository.transfer.assert_not_called()
    mock_repository.add_request.assert_not_called()


async def test_execute_address_rate_limit(
    user_id, solana_address, mock_repository, mock_blockchain_repository
):
    # Setup - address has a recent request
    mock_recent_request = SolanaFaucetRequest(
        id=UUID("218506ee-af34-4320-8a09-b6432dafc187"),
        user_profile_id=UUID("166e9449-c696-7462-8000-3196255ced8d"),  # different user
        solana_address=solana_address,
        transaction_signature="some_signature",
        created_at=datetime.datetime.now(),
    )
    mock_repository.get_recent_request_by_address.return_value = mock_recent_request

    # Execute and expect exception
    with pytest.raises(error_responses.RateLimitError) as exc_info:
        await solana_faucet_use_case.execute(
            user_id, solana_address, mock_repository, mock_blockchain_repository
        )

    # Assert error message contains rate limit info
    assert f"{settings.SOLANA_FAUCET_RATE_LIMIT_HOURS} hours" in str(exc_info.value)

    # Verify repository calls
    mock_repository.get_recent_request_by_user_profile_id.assert_called_once()
    mock_repository.get_recent_request_by_address.assert_called_once()
    mock_blockchain_repository.transfer.assert_not_called()
    mock_repository.add_request.assert_not_called()


async def test_execute_invalid_address(user_id, mock_repository, mock_blockchain_repository):
    # Setup - invalid address
    invalid_address = "invalid_address"

    # Execute and expect exception
    with pytest.raises(error_responses.ValidationTypeError) as exc_info:
        await solana_faucet_use_case.execute(
            user_id, invalid_address, mock_repository, mock_blockchain_repository
        )

    # Verify repository calls
    mock_repository.get_recent_request_by_user_profile_id.assert_called_once()
    mock_repository.get_recent_request_by_address.assert_called_once()
    mock_blockchain_repository.transfer.assert_not_called()
    mock_repository.add_request.assert_not_called()


async def test_execute_blockchain_error(
    user_id, solana_address, mock_repository, mock_blockchain_repository
):
    # Setup - blockchain error
    mock_blockchain_repository.transfer.side_effect = Exception("Blockchain error")

    # Execute and expect exception
    with pytest.raises(error_responses.InternalServerAPIError):
        await solana_faucet_use_case.execute(
            user_id, solana_address, mock_repository, mock_blockchain_repository
        )

    # Verify repository calls
    mock_repository.get_recent_request_by_user_profile_id.assert_called_once()
    mock_repository.get_recent_request_by_address.assert_called_once()
    mock_blockchain_repository.transfer.assert_called_once()
    mock_repository.add_request.assert_not_called()
