from fastapi import APIRouter, Depends

from distributedinference import api_logger
from distributedinference import dependencies
from distributedinference.domain.user.entities import User
from distributedinference.repository.blockchain_proof_repository import (
    BlockchainProofRepository,
)
from distributedinference.repository.solana_faucet_repository import (
    SolanaFaucetRepository,
)
from distributedinference.service.auth import authentication
from distributedinference.service.faucet import solana_faucet_service
from distributedinference.service.faucet.entities import (
    SolanaFaucetRequestModel,
    SolanaFaucetResponseModel,
)

TAG = "Faucet"
router = APIRouter(
    prefix="/faucet",
)
router.tags = [TAG]

logger = api_logger.get()


@router.post(
    "/solana",
    name="Solana Faucet",
    description="Send 0.0001 SOL to the provided Solana address from the Galadriel faucet.",
    response_model=SolanaFaucetResponseModel,
)
async def solana_faucet(
    request: SolanaFaucetRequestModel,
    user: User = Depends(authentication.validate_api_key_header),
    solana_faucet_repository: SolanaFaucetRepository = Depends(
        dependencies.get_solana_faucet_repository
    ),
    blockchain_repository: BlockchainProofRepository = Depends(
        dependencies.get_blockchain_proof_repository
    ),
) -> SolanaFaucetResponseModel:
    """Send 0.0001 SOL to the provided Solana address from the Galadriel faucet.

    Rate limited to once per day per API key and per Solana address.
    """
    response = await solana_faucet_service.execute(
        request,
        user,
        solana_faucet_repository,
        blockchain_repository,
    )

    return SolanaFaucetResponseModel(
        success=response.success,
        transaction_signature=response.transaction_signature,
        message=response.message,
    )
