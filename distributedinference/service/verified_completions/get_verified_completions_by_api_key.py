from typing import List

from distributedinference.repository.verified_completions_repository import (
    VerifiedCompletion,
    VerifiedCompletionsRepository,
)
from distributedinference.service.verified_completions.entities import (
    VerifiedChatCompletion,
)
from distributedinference.service.verified_completions.entities import (
    VerifiedChatCompletionsRequest,
)
from distributedinference.service.verified_completions.entities import (
    VerifiedChatCompletionsResponse,
)


async def execute(
    api_key: str,
    request: VerifiedChatCompletionsRequest,
    repository: VerifiedCompletionsRepository,
) -> VerifiedChatCompletionsResponse:
    completions = await repository.get_by_api_key(
        api_key, request.limit, request.cursor
    )
    cursor = completions[-1].id if len(completions) == request.limit else None
    return VerifiedChatCompletionsResponse(
        completions=_convert_completions(completions), cursor=cursor
    )


def _convert_completions(
    completions: List[VerifiedCompletion],
) -> List[VerifiedChatCompletion]:
    result = []
    for completion in completions:
        result.append(
            VerifiedChatCompletion(
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
        )
    return result
