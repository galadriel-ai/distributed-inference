from distributedinference.repository.verified_completions_repository import (
    VerifiedCompletionsRepository,
)
from distributedinference.service.verified_completions.entities import (
    PostVerifiedLogRequest,
)
from distributedinference.service.verified_completions.entities import (
    PostVerifiedLogResponse,
)


async def execute(
    api_key: str,
    request: PostVerifiedLogRequest,
    verified_completions_repository: VerifiedCompletionsRepository,
) -> PostVerifiedLogResponse:
    try:
        await verified_completions_repository.insert_verified_completion(
            api_key=api_key,
            request={"request": request.request},
            response={"response": request.response},
            hash=request.hash,
            public_key=request.public_key,
            signature=request.signature,
            attestation=request.attestation,
        )
        return PostVerifiedLogResponse(success=True)
    except:
        return PostVerifiedLogResponse(success=False)
