from typing import Dict

from fastapi import Response

from distributedinference.repository.tee_api_repository import TeeApiRepository
from distributedinference.repository.utils import utcnow
from distributedinference.repository.verified_completions_repository import (
    VerifiedCompletionsRepository,
)
from distributedinference.service import error_responses
from distributedinference.service.verified_completions.entities import (
    ChatCompletionRequest,
)


async def execute(
    api_key: str,
    request: ChatCompletionRequest,
    response: Response,
    tee_repository: TeeApiRepository,
    verified_completions_repository: VerifiedCompletionsRepository,
) -> Dict:
    if request.stream:
        raise NotImplementedError
    response_body = await tee_repository.completions(
        request.model_dump(exclude_unset=True)
    )
    if not response_body:
        raise error_responses.InternalServerAPIError()

    await _log_verified_completion(
        verified_completions_repository, api_key, request, response_body
    )
    return response_body


async def _log_verified_completion(
    verified_completions_repository: VerifiedCompletionsRepository,
    api_key: str,
    request: ChatCompletionRequest,
    response: Dict,
) -> None:
    exclude_keys = {
        "hash",
        "public_key",
        "signature",
        "attestation",
        "tx_hash",
    }
    original_response = {k: v for k, v in response.items() if k not in exclude_keys}

    await verified_completions_repository.insert_verified_completion(
        api_key=api_key,
        request=request.model_dump(),
        response=original_response,
        hash=response["hash"],
        public_key=response["public_key"],
        signature=response["signature"],
        attestation=response["attestation"],
        tx_hash=response["tx_hash"],
    )
