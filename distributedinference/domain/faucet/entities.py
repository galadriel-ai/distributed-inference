from dataclasses import dataclass
from datetime import datetime
from datetime import UTC
from typing import Optional
from uuid import UUID
from uuid_extensions import uuid7


@dataclass
class FaucetRequest:
    """Entity representing a faucet request."""

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        user_profile_id: UUID,
        chain: str,
        address: str,
        transaction_signature: str,
        request_id: Optional[UUID] = None,
        created_at: Optional[datetime] = None,
    ):
        self.id = request_id or uuid7()
        self.user_profile_id = user_profile_id
        self.chain = chain
        self.address = address
        self.transaction_signature = transaction_signature
        self.created_at = created_at or datetime.now(UTC)


@dataclass
class FaucetResponse:
    """Response for a faucet request."""

    def __init__(
        self,
        success: bool,
        transaction_signature: Optional[str] = None,
        message: Optional[str] = None,
    ):
        self.success = success
        self.transaction_signature = transaction_signature
        self.message = message
