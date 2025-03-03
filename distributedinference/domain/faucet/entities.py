from dataclasses import dataclass
from datetime import datetime
from datetime import UTC
from typing import Optional
from uuid import UUID
from uuid_extensions import uuid7


@dataclass
class FaucetRequest:
    """Entity representing a faucet request."""

    request_id: UUID
    user_profile_id: UUID
    chain: str
    address: str
    transaction_signature: str
    created_at: datetime


@dataclass
class FaucetResponse:
    """Response for a faucet request."""

    success: bool
    transaction_signature: Optional[str] = None
    message: Optional[str] = None
