from fastapi import APIRouter
from fastapi import Depends

from distributedinference import api_logger
from distributedinference import dependencies
from distributedinference.domain.user.entities import User
from distributedinference.repository.embedding_api_repository import (
    EmbeddingApiRepository,
)
from distributedinference.service.auth import authentication
from distributedinference.service.embedding import embedding_service
from distributedinference.service.embedding.entities import EmbeddingRequest
from distributedinference.service.embedding.entities import EmbeddingResponse

TAG = "Embeddings"
router = APIRouter(prefix="/embeddings")
router.tags = [TAG]

logger = api_logger.get()


@router.post(
    "",
    summary="Creates an embedding vector representing the input text.",
    description="Given a list of strings return embeddings for them.",
    response_description="Returns a list of embeddings.",
    response_model=EmbeddingResponse,
)
async def completions(
    request: EmbeddingRequest,
    embedding_repository: EmbeddingApiRepository = Depends(
        dependencies.get_embedding_api_repository
    ),
    _: User = Depends(authentication.validate_api_key_header),
):
    return await embedding_service.execute(request, embedding_repository)
