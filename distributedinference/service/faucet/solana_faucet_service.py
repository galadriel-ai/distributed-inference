from distributedinference import api_logger
from distributedinference.domain.faucet import solana_faucet_use_case
from distributedinference.domain.faucet.entities import SolanaFaucetResponse
from distributedinference.domain.user.entities import User
from distributedinference.repository.blockchain_proof_repository import BlockchainProofRepository
from distributedinference.repository.solana_faucet_repository import SolanaFaucetRepository
from distributedinference.domain.faucet.entities import SolanaFaucetRequest
from distributedinference.utils.timer import async_timer

logger = api_logger.get()


@async_timer("solana_faucet_service.execute", logger=logger)
async def execute(
    request: SolanaFaucetRequest,
    user: User,
    solana_faucet_repository: SolanaFaucetRepository,
    blockchain_repository: BlockchainProofRepository,
) -> SolanaFaucetResponse:
    """Process a Solana faucet request."""
    return await solana_faucet_use_case.execute(
        user.uid,
        request.address,
        solana_faucet_repository,
        blockchain_repository,
    )
