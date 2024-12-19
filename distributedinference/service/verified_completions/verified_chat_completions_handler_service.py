from typing import Dict

import hashlib

from fastapi import Response

from distributedinference import api_logger
from distributedinference.repository.blockchain_proof_repository import (
    AttestationProof,
    BlockchainProofRepository,
)
from distributedinference.repository.tee_api_repository import TeeApiRepository
from distributedinference.service import error_responses
from distributedinference.service.verified_completions.entities import (
    ChatCompletionRequest,
)

logger = api_logger.get()


async def execute(
    request: ChatCompletionRequest,
    response: Response,
    tee_repository: TeeApiRepository,
    blockchain_proof_repository: BlockchainProofRepository,
) -> Dict:
    if request.stream:
        raise NotImplementedError
    response_body = await tee_repository.completions(
        request.model_dump(exclude_unset=True)
    )
    if not response_body:
        raise error_responses.InternalServerAPIError()

    try:
        attestation_doc = response_body["attestation"]
        attestation_hash = hashlib.sha256(attestation_doc.encode()).digest()

        proof = AttestationProof(
            hashed_data=bytes.fromhex(response_body["hash"]),
            public_key=bytes.fromhex(response_body["public_key"]),
            signature=bytes.fromhex(response_body["signature"]),
            attestation=attestation_hash,
        )
        tx_response = await blockchain_proof_repository.add_proof(proof)

        if not tx_response:
            raise error_responses.InternalServerAPIError()

        response_body["tx_hash"] = str(tx_response.value)
        return response_body
    except Exception as e:
        logger.error(f"Error adding proof to blockchain: {e}")
        raise error_responses.InternalServerAPIError()
