from typing import List

import settings
from distributedinference.domain.embedding import create_embeddings_use_case
from distributedinference.domain.embedding.entities import EmbeddingApiError
from distributedinference.repository.embedding_api_repository import (
    EmbeddingApiRepository,
)
from distributedinference.service import error_responses
from distributedinference.service.embedding.entities import EmbeddingObject
from distributedinference.service.embedding.entities import EmbeddingRequest
from distributedinference.service.embedding.entities import EmbeddingResponse

MAX_BATCH_SIZE: int = 32


async def execute(
    request: EmbeddingRequest,
    repository: EmbeddingApiRepository,
) -> EmbeddingResponse:
    if request.model not in settings.SUPPORTED_EMBEDDING_MODELS:
        raise error_responses.UnsupportedModelError(model_name=request.model)

    input_texts = await _get_input_texts(request)
    if len(input_texts) > MAX_BATCH_SIZE:
        raise error_responses.ValidationTypeError(
            f"Maximum input array size for embeddings is {MAX_BATCH_SIZE}"
        )
    embeddings = await _get_embedding_result(input_texts, repository)
    return EmbeddingResponse(
        object="list",
        data=_format_embeddings(embeddings),
        model=request.model,
    )


async def _get_input_texts(request: EmbeddingRequest) -> List[str]:
    input_texts = request.input
    if not isinstance(input_texts, list):
        input_texts = [input_texts]
    return input_texts


async def _get_embedding_result(
    input_texts: List[str], repository: EmbeddingApiRepository
) -> List[List[float]]:
    try:
        embeddings = await create_embeddings_use_case.execute(input_texts, repository)
    except EmbeddingApiError as exc:
        raise error_responses.EmbeddingError(exc.status, exc.message)
    except Exception as _:
        raise error_responses.InternalServerAPIError()
    return embeddings


def _format_embeddings(embeddings: List[List[float]]) -> List[EmbeddingObject]:
    return [
        EmbeddingObject(
            index=i,
            embedding=embedding,
            object="embedding",
        )
        for i, embedding in enumerate(embeddings)
    ]
