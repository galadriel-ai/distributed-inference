from decimal import Decimal
from datetime import datetime
from datetime import UTC
from uuid import UUID
from uuid_extensions import uuid7

from solders.pubkey import Pubkey  # type: ignore # pylint: disable=import-error
from solana.constants import LAMPORTS_PER_SOL

import settings
from distributedinference import api_logger
from distributedinference.domain.faucet.entities import (
    FaucetRequest,
    FaucetResponse,
)
from distributedinference.repository.blockchain_proof_repository import (
    BlockchainProofRepository,
)
from distributedinference.repository.faucet_repository import (
    FaucetRepository,
)
from distributedinference.service import error_responses

# Amount of SOL to send from settings
FAUCET_AMOUNT = Decimal(settings.SOLANA_FAUCET_AMOUNT)
FAUCET_CHAIN = "solana"

logger = api_logger.get()


async def execute(
    address: str,
    repository: FaucetRepository,
    blockchain_repository: BlockchainProofRepository,
) -> FaucetResponse:
    """Process a Solana faucet request."""

    # Check if the address has received any airdrop recently
    recent_address_request = await repository.get_recent_request_by_address(
        address, FAUCET_CHAIN
    )
    if recent_address_request:
        raise error_responses.RateLimitError(
            {
                "error": f"Rate limit exceeded. This address has already received an airdrop in the last {settings.SOLANA_FAUCET_RATE_LIMIT_HOURS} hours."
            }
        )

    try:
        # Calculate lamports to send
        lamports = int(FAUCET_AMOUNT * LAMPORTS_PER_SOL)

        # Send the SOL to the provided address
        recipient_pubkey = Pubkey.from_string(address)

        # Execute the transfer
        tx_result = await blockchain_repository.transfer(recipient_pubkey, lamports)

        # Create and save the request with the transaction signature
        request = FaucetRequest(
            request_id=uuid7(),
            chain=FAUCET_CHAIN,
            address=address,
            transaction_signature=str(tx_result.value),
            created_at=datetime.now(UTC),
        )

        # Save the successful request to the database
        _request_id = await repository.add_request(request)

        return FaucetResponse(
            success=True,
            transaction_signature=str(tx_result.value),
            message=f"Successfully sent {FAUCET_AMOUNT} SOL",
        )
    except error_responses.APIErrorResponse as e:
        raise e
    except ValueError as e:
        raise error_responses.ValidationTypeError(str(e)) from e
    except Exception as e:
        logger.error(f"Error sending SOL: {str(e)}")
        raise error_responses.InternalServerAPIError()
