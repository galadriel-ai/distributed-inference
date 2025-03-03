from decimal import Decimal
from uuid import UUID

import settings
from distributedinference import api_logger
from distributedinference.domain.faucet.entities import (
    SolanaFaucetRequest,
    SolanaFaucetResponse,
)
from distributedinference.repository.blockchain_proof_repository import BlockchainProofRepository
from distributedinference.repository.solana_faucet_repository import SolanaFaucetRepository
from distributedinference.service import error_responses

from solders.pubkey import Pubkey  # type: ignore # pylint: disable=import-error
from solana.constants import LAMPORTS_PER_SOL

# Amount of SOL to send from settings
FAUCET_AMOUNT = Decimal(settings.SOLANA_FAUCET_AMOUNT)

logger = api_logger.get()


async def execute(
    user_profile_id: UUID,
    solana_address: str,
    repository: SolanaFaucetRepository,
    blockchain_repository: BlockchainProofRepository,
) -> SolanaFaucetResponse:
    """Process a Solana faucet request."""

    # Check if the user has made any request in the last X hours based on settings
    recent_user_request = await repository.get_recent_request_by_user_profile_id(user_profile_id)
    if recent_user_request:
        raise error_responses.RateLimitError(
            {
                "error": f"Rate limit exceeded. You can only make one request every {settings.SOLANA_FAUCET_RATE_LIMIT_HOURS} hours."
            }
        )

    # Check if the address has received any airdrop in the last X hours based on settings
    recent_address_request = await repository.get_recent_request_by_address(solana_address)
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
        recipient_pubkey = Pubkey.from_string(solana_address)

        # Execute the transfer
        tx_result = await blockchain_repository.transfer(recipient_pubkey, lamports)

        # Create and save the request with the transaction signature
        request = SolanaFaucetRequest(
            user_profile_id=user_profile_id,
            solana_address=solana_address,
            transaction_signature=str(tx_result.value),
        )

        # Save the successful request to the database
        _request_id = await repository.add_request(request)

        return SolanaFaucetResponse(
            success=True,
            transaction_signature=str(tx_result.value),
            message=f"Successfully sent {settings.SOLANA_FAUCET_AMOUNT} SOL",
        )
    except error_responses.APIErrorResponse as e:
        raise e
    except ValueError as e:
        raise error_responses.ValidationTypeError(str(e)) from e
    except Exception as e:
        logger.error(f"Error sending SOL: {str(e)}")
        raise error_responses.InternalServerAPIError()
