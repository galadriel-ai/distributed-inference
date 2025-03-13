from fastapi import APIRouter, Depends

from distributedinference import api_logger
from distributedinference import dependencies
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

TAG = "Faucet"
router = APIRouter(
    prefix="/faucet",
)
router.tags = [TAG]

logger = api_logger.get()


@router.post(
    "/solana",
    name="Solana Faucet",
    description="Send a small amount of SOL to the provided Solana address from the Galadriel faucet.",
    response_model=SolanaFaucetResponseModel,
)
async def solana_faucet(
    request: SolanaFaucetRequestModel,
    faucet_repository: FaucetRepository = Depends(dependencies.get_faucet_repository),
    blockchain_repository: BlockchainProofRepository = Depends(
        dependencies.get_blockchain_proof_mainnet_repository
    ),
) -> SolanaFaucetResponseModel:
    """Send a small amount of SOL to the provided Solana address from the Galadriel faucet using mainnet.

    Rate limited per Solana address.
    """
    response = await solana_faucet_service.execute(
        request,
        faucet_repository,
        blockchain_repository,
    )

    return SolanaFaucetResponseModel(
        success=response.success,
        transaction_signature=response.transaction_signature,
        message=response.message,
    )
