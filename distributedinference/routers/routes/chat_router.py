from fastapi import APIRouter
from fastapi import Depends

from distributedinference import api_logger
from distributedinference.domain.user.entities import User
from distributedinference.service.auth import authentication
from distributedinference.service.completions import chat_completions_service
from distributedinference.service.completions.entities import ChatCompletionRequest
from distributedinference.service.completions.entities import ChatCompletion

TAG = "Agent"
router = APIRouter(
    prefix="/chat"
)
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
    validated_user: User = Depends(authentication.validate_api_key),
):
    return await chat_completions_service.execute(request)
