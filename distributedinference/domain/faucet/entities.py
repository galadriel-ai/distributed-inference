from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4


class SolanaFaucetRequest:
    """Entity representing a Solana faucet request."""

    def __init__(
        self,
        user_profile_id: UUID,
        solana_address: str,
        transaction_signature: str,
        id: Optional[UUID] = None,
        created_at: Optional[datetime] = None,
    ):
        self.id = id or uuid4()
        self.user_profile_id = user_profile_id
        self.solana_address = solana_address
        self.transaction_signature = transaction_signature
        self.created_at = created_at or datetime.now()


class SolanaFaucetResponse:
    """Response for a Solana faucet request."""

    def __init__(
        self,
        success: bool,
        transaction_signature: Optional[str] = None,
        message: Optional[str] = None,
    ):
        self.success = success
        self.transaction_signature = transaction_signature
        self.message = message
