from typing import Optional
from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Path
from fastapi import Query
from fastapi import Request
from fastapi import Response

from distributedinference import api_logger
from distributedinference import dependencies
from distributedinference.analytics.analytics import Analytics
from distributedinference.analytics.analytics import AnalyticsEvent
from distributedinference.analytics.analytics import EventName
from distributedinference.domain.user.entities import User
from distributedinference.repository.tee_api_repository import TeeApiRepository
from distributedinference.service.auth import authentication
from distributedinference.service.verified_completions import (
    verified_chat_completions_handler_service,
    get_verified_completions,
    get_verified_completions_by_api_key,
    get_verified_completion_by_hash,
)
from distributedinference.service.verified_completions.entities import ChatCompletion
from distributedinference.service.verified_completions.entities import (
    ChatCompletionRequest,
    VerifiedChatCompletion,
    VerifiedChatCompletionFilter,
    VerifiedChatCompletionsRequest,
    VerifiedChatCompletionsResponse,
)

TAG = "Verified Chat"
router = APIRouter(prefix="/verified/chat")
router.tags = [TAG]

logger = api_logger.get()


@router.post(
    "/completions",
    summary="Creates a model response for the given chat conversation.",
    description="Given a list of messages comprising a conversation, the model will return a response.",
    response_description="Returns a chat completion object, or a streamed sequence of chat completion chunk objects if the request is streamed.",
    response_model=ChatCompletion,
)
async def completions(
    api_request: Request,
    request: ChatCompletionRequest,
    response: Response,
    user: User = Depends(authentication.validate_api_key_header),
    tee_repository: TeeApiRepository = Depends(dependencies.get_tee_repository),
    verified_completions_repository=Depends(
        dependencies.get_verified_completions_repository
    ),
    analytics: Analytics = Depends(dependencies.get_analytics),
):
    analytics.track_event(
        user.uid, AnalyticsEvent(EventName.VERIFIED_CHAT_COMPLETIONS, {})
    )
    api_key = _get_api_key(api_request)
    return await verified_chat_completions_handler_service.execute(
        api_key, request, response, tee_repository, verified_completions_repository
    )


@router.get(
    "/completions",
    summary="Retrieves all agent verified chat completions.",
    description="Retrieves all agent verified chat completions.",
    response_description="Returns a list of chat completion objects.",
    response_model=VerifiedChatCompletionsResponse,
)
async def get_completions(
    api_request: Request,
    limit: Optional[int] = Query(
        100, description="The maximum number of completions to retrieve."
    ),
    cursor: Optional[UUID] = Query(None, description="The cursor for pagination."),
    filter: Optional[VerifiedChatCompletionFilter] = Query(
        None,
        description="Filter completions. Use `mine` to retrieve your own completions.",
    ),
    user: User = Depends(authentication.validate_api_key_header),
    verified_completions_repository=Depends(
        dependencies.get_verified_completions_repository
    ),
):
    request = VerifiedChatCompletionsRequest(limit=limit, cursor=cursor)
    if filter == VerifiedChatCompletionFilter.MINE:
        api_key = _get_api_key(api_request)
        return await get_verified_completions_by_api_key.execute(
            api_key, request, verified_completions_repository
        )
    return await get_verified_completions.execute(
        request, verified_completions_repository
    )


@router.get(
    "/completions/{hash}",
    summary="Retrieves a verified chat completion by hash.",
    description="Retrieve a verified chat completion by hash.",
    response_description="Returns a verified chat completion object.",
    response_model=VerifiedChatCompletion,
)
async def get_completion_by_hash(
    hash: str = Path(..., description="The hash of the verified completion."),
    user: User = Depends(authentication.validate_api_key_header),
    verified_completions_repository=Depends(
        dependencies.get_verified_completions_repository
    ),
):
    return await get_verified_completion_by_hash.execute(
        hash, verified_completions_repository
    )


def _get_api_key(
    request: Request,
) -> str:
    api_key_header = request.headers.get("Authorization") or ""
    api_key_header = api_key_header.replace("Bearer ", "")
    return api_key_header
