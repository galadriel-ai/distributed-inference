from distributedinference.service import error_responses
from distributedinference.repository.verified_completions_repository import (
    VerifiedCompletion,
    VerifiedCompletionsRepository,
)
from distributedinference.service.verified_completions.entities import (
    VerifiedChatCompletion,
)


async def execute(
    hash: str, repository: VerifiedCompletionsRepository
) -> VerifiedChatCompletion:
    completion = await repository.get_by_hash(hash)
    if not completion:
        raise error_responses.NotFoundAPIError(f"verified completion with hash {hash}")
    return _convert_completion(completion)


def _convert_completion(completion: VerifiedCompletion) -> VerifiedChatCompletion:
    return VerifiedChatCompletion(
        id=str(completion.id),
        request=completion.request,
        response=completion.response,
        hash=completion.hash,
        public_key=completion.public_key,
        signature=completion.signature,
        attestation=completion.attestation,
        tx_hash=completion.tx_hash,
        created_at=int(completion.created_at.timestamp()),
    )
