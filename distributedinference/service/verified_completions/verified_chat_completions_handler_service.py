from typing import Dict

from fastapi import Response

from distributedinference.repository.tee_api_repository import TeeApiRepository
from distributedinference.service import error_responses
from distributedinference.service.verified_completions.entities import (
    ChatCompletionRequest,
)


async def execute(
    request: ChatCompletionRequest,
    response: Response,
    tee_repository: TeeApiRepository,
) -> Dict:
    if request.stream:
        raise NotImplementedError
    response_body = await tee_repository.completions(
        request.model_dump(exclude_unset=True)
    )
    if not response_body:
        raise error_responses.InternalServerAPIError()
    return response_body
