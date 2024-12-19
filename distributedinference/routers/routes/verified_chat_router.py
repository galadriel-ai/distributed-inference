from fastapi import APIRouter
from fastapi import Depends
from fastapi import Response

from distributedinference import api_logger
from distributedinference import dependencies
from distributedinference.analytics.analytics import Analytics
from distributedinference.analytics.analytics import AnalyticsEvent
from distributedinference.analytics.analytics import EventName
from distributedinference.domain.user.entities import User
from distributedinference.repository.blockchain_proof_repository import BlockchainProofRepository
from distributedinference.repository.tee_api_repository import TeeApiRepository
from distributedinference.service.auth import authentication
from distributedinference.service.verified_completions import (
    verified_chat_completions_handler_service,
)
from distributedinference.service.verified_completions.entities import ChatCompletion
from distributedinference.service.verified_completions.entities import (
    ChatCompletionRequest,
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
    request: ChatCompletionRequest,
    response: Response,
    user: User = Depends(authentication.validate_api_key_header),
    tee_repository: TeeApiRepository = Depends(dependencies.get_tee_repository),
    blockchain_proof_repository: BlockchainProofRepository = Depends(
        dependencies.get_blockchain_proof_repository
    ),
    analytics: Analytics = Depends(dependencies.get_analytics),
):
    analytics.track_event(
        user.uid, AnalyticsEvent(EventName.VERIFIED_CHAT_COMPLETIONS, {})
    )
    return await verified_chat_completions_handler_service.execute(
        request, response, tee_repository, blockchain_proof_repository
    )
