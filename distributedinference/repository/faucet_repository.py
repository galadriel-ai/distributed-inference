from typing import Optional
from uuid import UUID

import sqlalchemy

import settings
from distributedinference import api_logger
from distributedinference.domain.faucet.entities import FaucetRequest
from distributedinference.repository.connection import SessionProvider
from distributedinference.utils.timer import async_timer


# SQL query to check if an address has received ANY request in the last X hours based on settings
SQL_GET_RECENT_REQUEST_BY_ADDRESS = f"""
SELECT
    id,
    chain,
    address,
    transaction_signature,
    created_at
FROM faucet_request
WHERE address = :address
AND chain = :chain
AND created_at > (NOW() AT TIME ZONE 'UTC') - INTERVAL '{settings.SOLANA_FAUCET_RATE_LIMIT_HOURS} hours'
ORDER BY created_at DESC
LIMIT 1;
"""

# SQL query to insert a new faucet request
SQL_INSERT_REQUEST = """
INSERT INTO faucet_request (
    id,
    chain,
    address,
    transaction_signature,
    created_at
) VALUES (
    :id,
    :chain,
    :address,
    :transaction_signature,
    :created_at
) RETURNING id;
"""

logger = api_logger.get()


class FaucetRepository:

    def __init__(
        self, session_provider: SessionProvider, session_provider_read: SessionProvider
    ):
        self._session_provider = session_provider
        self._session_provider_read = session_provider_read

    @async_timer("faucet_repository.get_recent_request_by_address", logger=logger)
    async def get_recent_request_by_address(
        self, address: str, chain: str
    ) -> Optional[FaucetRequest]:
        """Get the most recent faucet request for a specific address in the last X hours based on settings."""
        data = {"address": address, "chain": chain}
        async with self._session_provider_read.get() as session:
            result = await session.execute(
                sqlalchemy.text(SQL_GET_RECENT_REQUEST_BY_ADDRESS), data
            )
            row = result.fetchone()
            if row:
                return FaucetRequest(
                    request_id=row.id,
                    chain=row.chain,
                    address=row.address,
                    transaction_signature=row.transaction_signature,
                    created_at=row.created_at,
                )
            return None

    @async_timer("faucet_repository.add_request", logger=logger)
    async def add_request(self, request: FaucetRequest) -> UUID:
        """Add a new faucet request to the database."""
        transaction_signature = str(request.transaction_signature)

        data = {
            "id": request.request_id,
            "chain": request.chain,
            "address": request.address,
            "transaction_signature": transaction_signature,
            "created_at": request.created_at,
        }
        async with self._session_provider.get() as session:
            result = await session.execute(sqlalchemy.text(SQL_INSERT_REQUEST), data)
            await session.commit()
            return result.scalar_one()
