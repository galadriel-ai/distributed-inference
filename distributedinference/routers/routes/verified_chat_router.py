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
from distributedinference.repository.blockchain_proof_repository import (
    BlockchainProofRepository,
)
from distributedinference.repository.rate_limit_repository import RateLimitRepository
from distributedinference.repository.tee_api_repository import TeeApiRepository
from distributedinference.repository.tokens_queue_repository import (
    TokensQueueRepository,
)
from distributedinference.repository.tokens_repository import TokensRepository
from distributedinference.service.auth import authentication
from distributedinference.service.verified_completions import post_verified_log_service
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
from distributedinference.service.verified_completions.entities import (
    PostVerifiedLogRequest,
)
from distributedinference.service.verified_completions.entities import (
    PostVerifiedLogResponse,
)

TAG = "Verified Chat"
router = APIRouter(prefix="/verified/chat")
router.tags = [TAG]

logger = api_logger.get()


# pylint: disable=too-many-arguments
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
    rate_limit_repository: RateLimitRepository = Depends(
        dependencies.get_rate_limit_repository
    ),
    tee_repository: TeeApiRepository = Depends(dependencies.get_tee_repository),
    tokens_repository: TokensRepository = Depends(dependencies.get_tokens_repository),
    tokens_queue_repository: TokensQueueRepository = Depends(
        dependencies.get_tokens_queue_repository
    ),
    blockchain_proof_repository: BlockchainProofRepository = Depends(
        dependencies.get_blockchain_proof_repository
    ),
    verified_completions_repository=Depends(
        dependencies.get_verified_completions_repository
    ),
    analytics: Analytics = Depends(dependencies.get_analytics),
):
    analytics.track_event(
        user.uid, AnalyticsEvent(EventName.VERIFIED_CHAT_COMPLETIONS, {})
    )
    galadriel_api_key = _get_galadriel_api_key(api_request)

    fine_tune_api_key = _get_fine_tune_api_key(api_request)

    return await verified_chat_completions_handler_service.execute(
        galadriel_api_key,
        fine_tune_api_key,
        user,
        request,
        response,
        rate_limit_repository,
        tee_repository,
        tokens_repository,
        tokens_queue_repository,
        blockchain_proof_repository,
        verified_completions_repository,
        analytics,
    )


# pylint: disable=W0622,
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
    _: User = Depends(authentication.validate_api_key_header),
    verified_completions_repository=Depends(
        dependencies.get_verified_completions_repository
    ),
):
    request = VerifiedChatCompletionsRequest(limit=limit, cursor=cursor)
    if filter == VerifiedChatCompletionFilter.MINE:
        api_key = _get_galadriel_api_key(api_request)
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
    _: User = Depends(authentication.validate_api_key_header),
    verified_completions_repository=Depends(
        dependencies.get_verified_completions_repository
    ),
):
    return await get_verified_completion_by_hash.execute(
        hash, verified_completions_repository
    )


@router.post(
    "/log",
    summary="Creates a new verified log entry",
    description="",
    response_description="Post Verified Log Response",
    response_model=PostVerifiedLogResponse,
)
async def create_agent(
    api_request: Request,
    request: PostVerifiedLogRequest,
    verified_completions_repository=Depends(
        dependencies.get_verified_completions_repository
    ),
):
    galadriel_api_key = _get_galadriel_api_key(api_request)
    return await post_verified_log_service.execute(
        api_key=galadriel_api_key,
        request=request,
        verified_completions_repository=verified_completions_repository,
    )


def _get_galadriel_api_key(
    request: Request,
) -> str:
    api_key_header = request.headers.get("Authorization") or ""
    api_key_header = api_key_header.replace("Bearer ", "")
    return api_key_header


# Get user's API key for the fine-tune models of OpenAI or Anthropic
def _get_fine_tune_api_key(
    request: Request,
) -> Optional[str]:
    api_key_header = request.headers.get("Fine-Tune-Authorization")
    return api_key_header.replace("Bearer ", "") if api_key_header else None
