import json

from datetime import datetime
from dataclasses import dataclass
from typing import Dict
from typing import List
from typing import Optional
from uuid import UUID

import sqlalchemy
from uuid_extensions import uuid7

from distributedinference import api_logger
from distributedinference.repository.connection import SessionProvider
from distributedinference.repository.utils import utcnow
from distributedinference.utils.timer import async_timer


@dataclass
class VerifiedCompletion:
    id: UUID
    api_key: str
    request: Dict
    response: Dict
    hash: str
    public_key: str
    signature: str
    attestation: str
    tx_hash: str
    created_at: datetime
    updated_at: datetime


SQL_INSERT = """
INSERT INTO verified_completions (
    id,
    hash,
    api_key,
    request,
    response,
    public_key,
    signature,
    attestation,
    tx_hash,
    created_at,
    last_updated_at
)
VALUES (
    :id,
    :hash,
    :api_key,
    :request,
    :response,
    :public_key,
    :signature,
    :attestation,
    :tx_hash,
    :created_at,
    :last_updated_at
);
"""

SQL_GET = """
SELECT
    id,
    hash,
    api_key,
    request,
    response,
    public_key,
    signature,
    attestation,
    tx_hash,
    created_at,
    last_updated_at
FROM verified_completions
WHERE id > :cursor
ORDER BY id ASC
LIMIT :limit;
"""

SQL_GET_BY_API_KEY = """
SELECT
    id,
    hash,
    api_key,
    request,
    response,
    public_key,
    signature,
    attestation,
    tx_hash,
    created_at,
    last_updated_at
FROM verified_completions
WHERE api_key = :api_key AND id > :cursor
ORDER BY id ASC
LIMIT :limit;
"""

SQL_GET_BY_HASH = """
SELECT
    id,
    hash,
    api_key,
    request,
    response,
    public_key,
    signature,
    attestation,
    tx_hash,
    created_at,
    last_updated_at
FROM verified_completions
WHERE 
    hash = :hash;
"""

logger = api_logger.get()


class VerifiedCompletionsRepository:

    def __init__(
        self, session_provider: SessionProvider, session_provider_read: SessionProvider
    ):
        self._session_provider = session_provider
        self._session_provider_read = session_provider_read

    @async_timer(
        "verified_completions_repository.insert_verified_completion", logger=logger
    )
    async def insert_verified_completion(
        self,
        api_key: str,
        request: Dict,
        response: Dict,
        hash: str,
        public_key: str,
        signature: str,
        attestation: str,
        tx_hash: str,
    ):
        data = {
            "id": uuid7(),
            "api_key": api_key,
            "request": json.dumps(request),
            "response": json.dumps(response),
            "hash": hash,
            "public_key": public_key,
            "signature": signature,
            "attestation": attestation,
            "tx_hash": tx_hash,
            "created_at": utcnow(),
            "last_updated_at": utcnow(),
        }
        async with self._session_provider.get() as session:
            await session.execute(sqlalchemy.text(SQL_INSERT), data)
            await session.commit()

    @async_timer("verified_completions_repository.get", logger=logger)
    async def get(
        self, limit: int = 100, cursor: Optional[UUID] = None
    ) -> List[VerifiedCompletion]:
        data = {
            "limit": limit,
            "cursor": str(cursor) if cursor else "00000000-0000-0000-0000-000000000000",
        }
        result = []
        async with self._session_provider_read.get() as session:
            rows = await session.execute(sqlalchemy.text(SQL_GET), data)
            for row in rows:
                result.append(
                    VerifiedCompletion(
                        id=row.id,
                        api_key=row.api_key,
                        request=row.request,
                        response=row.response,
                        hash=row.hash,
                        public_key=row.public_key,
                        signature=row.signature,
                        attestation=row.attestation,
                        tx_hash=row.tx_hash,
                        created_at=row.created_at,
                        updated_at=row.last_updated_at,
                    )
                )
        return result

    @async_timer("verified_completions_repository.get_by_api_key", logger=logger)
    async def get_by_api_key(
        self, api_key: str, limit: int = 100, cursor: Optional[UUID] = None
    ) -> List[VerifiedCompletion]:
        data = {
            "api_key": api_key,
            "limit": limit,
            "cursor": str(cursor) if cursor else "00000000-0000-0000-0000-000000000000",
        }
        result = []
        async with self._session_provider_read.get() as session:
            rows = await session.execute(sqlalchemy.text(SQL_GET_BY_API_KEY), data)
            for row in rows:
                result.append(
                    VerifiedCompletion(
                        id=row.id,
                        api_key=row.api_key,
                        request=row.request,
                        response=row.response,
                        hash=row.hash,
                        public_key=row.public_key,
                        signature=row.signature,
                        attestation=row.attestation,
                        tx_hash=row.tx_hash,
                        created_at=row.created_at,
                        updated_at=row.last_updated_at,
                    )
                )
        return result

    @async_timer("verified_completions_repository.get_by_hash", logger=logger)
    async def get_by_hash(self, hash: str) -> Optional[VerifiedCompletion]:
        data = {"hash": hash}
        async with self._session_provider_read.get() as session:
            result = await session.execute(sqlalchemy.text(SQL_GET_BY_HASH), data)
            row = result.first()
            if row:
                return VerifiedCompletion(
                    id=row.id,
                    api_key=row.api_key,
                    request=row.request,
                    response=row.response,
                    hash=row.hash,
                    public_key=row.public_key,
                    signature=row.signature,
                    attestation=row.attestation,
                    tx_hash=row.tx_hash,
                    created_at=row.created_at,
                    updated_at=row.last_updated_at,
                )
        return None
