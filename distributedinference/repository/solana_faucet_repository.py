from typing import Optional
from uuid import UUID

import sqlalchemy

import settings
from distributedinference import api_logger
from distributedinference.domain.faucet.entities import (
    SolanaFaucetRequest,
)
from distributedinference.repository.connection import SessionProvider
from distributedinference.utils.timer import async_timer

# SQL query to check if a user has made ANY request in the last X hours based on settings
SQL_GET_RECENT_REQUEST_BY_USER = f"""
SELECT
    id,
    user_profile_id,
    solana_address,
    transaction_signature,
    created_at
FROM solana_faucet_request
WHERE user_profile_id = :user_profile_id
AND created_at > NOW() - INTERVAL '{settings.SOLANA_FAUCET_RATE_LIMIT_HOURS} hours'
ORDER BY created_at DESC
LIMIT 1;
"""

# SQL query to check if a Solana address has received ANY request in the last X hours based on settings
SQL_GET_RECENT_REQUEST_BY_ADDRESS = f"""
SELECT
    id,
    user_profile_id,
    solana_address,
    transaction_signature,
    created_at
FROM solana_faucet_request
WHERE solana_address = :solana_address
AND created_at > NOW() - INTERVAL '{settings.SOLANA_FAUCET_RATE_LIMIT_HOURS} hours'
ORDER BY created_at DESC
LIMIT 1;
"""

# SQL query to insert a new faucet request
SQL_INSERT_REQUEST = """
INSERT INTO solana_faucet_request (
    id,
    user_profile_id,
    solana_address,
    transaction_signature,
    created_at
) VALUES (
    :id,
    :user_profile_id,
    :solana_address,
    :transaction_signature,
    :created_at
) RETURNING id;
"""

logger = api_logger.get()


class SolanaFaucetRepository:
    def __init__(
        self, session_provider: SessionProvider, session_provider_read: SessionProvider
    ):
        self._session_provider = session_provider
        self._session_provider_read = session_provider_read

    @async_timer(
        "solana_faucet_repository.get_recent_request_by_user_profile_id", logger=logger
    )
    async def get_recent_request_by_user_profile_id(
        self, user_profile_id: UUID
    ) -> Optional[SolanaFaucetRequest]:
        """Get the most recent faucet request by a user in the last X hours based on settings."""
        data = {"user_profile_id": user_profile_id}
        async with self._session_provider_read.get() as session:
            result = await session.execute(
                sqlalchemy.text(SQL_GET_RECENT_REQUEST_BY_USER), data
            )
            row = result.fetchone()
            if row:
                return SolanaFaucetRequest(
                    request_id=row.id,
                    user_profile_id=row.user_profile_id,
                    solana_address=row.solana_address,
                    transaction_signature=row.transaction_signature,
                    created_at=row.created_at,
                )
            return None

    @async_timer(
        "solana_faucet_repository.get_recent_request_by_address", logger=logger
    )
    async def get_recent_request_by_address(
        self, solana_address: str
    ) -> Optional[SolanaFaucetRequest]:
        """Get the most recent faucet request for a specific Solana address in the last X hours based on settings."""
        data = {"solana_address": solana_address}
        async with self._session_provider_read.get() as session:
            result = await session.execute(
                sqlalchemy.text(SQL_GET_RECENT_REQUEST_BY_ADDRESS), data
            )
            row = result.fetchone()
            if row:
                return SolanaFaucetRequest(
                    request_id=row.id,
                    user_profile_id=row.user_profile_id,
                    solana_address=row.solana_address,
                    transaction_signature=row.transaction_signature,
                    created_at=row.created_at,
                )
            return None

    @async_timer("solana_faucet_repository.add_request", logger=logger)
    async def add_request(self, request: SolanaFaucetRequest) -> UUID:
        """Add a new faucet request to the database."""
        data = {
            "id": request.id,
            "user_profile_id": request.user_profile_id,
            "solana_address": request.solana_address,
            "transaction_signature": request.transaction_signature,
            "created_at": request.created_at,
        }
        async with self._session_provider.get() as session:
            result = await session.execute(sqlalchemy.text(SQL_INSERT_REQUEST), data)
            await session.commit()
            return result.scalar_one()
