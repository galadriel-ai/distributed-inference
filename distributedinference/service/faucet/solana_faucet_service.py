from distributedinference import api_logger
from distributedinference.domain.faucet import solana_faucet_use_case
from distributedinference.domain.faucet.entities import FaucetResponse
from distributedinference.domain.user.entities import User
from distributedinference.repository.blockchain_proof_repository import (
    BlockchainProofRepository,
)
from distributedinference.repository.faucet_repository import (
    FaucetRepository,
)
from distributedinference.service.faucet.entities import SolanaFaucetRequestModel
from distributedinference.utils.timer import async_timer

logger = api_logger.get()


@async_timer("solana_faucet_service.execute", logger=logger)
async def execute(
    request: SolanaFaucetRequestModel,
    user: User,
    faucet_repository: FaucetRepository,
    blockchain_repository: BlockchainProofRepository,
) -> FaucetResponse:
    """Process a Solana faucet request."""
    return await solana_faucet_use_case.execute(
        user.uid,
        request.address,
        faucet_repository,
        blockchain_repository,
    )
