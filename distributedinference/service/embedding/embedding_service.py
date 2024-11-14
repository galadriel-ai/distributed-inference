from typing import List
from typing import Literal
from typing import Optional
from typing import Union

from openai.types import CreateEmbeddingResponse

import settings
from distributedinference.domain.embedding import create_embeddings_use_case
from distributedinference.domain.embedding.entities import EmbeddingApiError
from distributedinference.repository.embedding_api_repository import (
    EmbeddingApiRepository,
)
from distributedinference.service import error_responses
from distributedinference.service.embedding.entities import EmbeddingRequest

MAX_BATCH_SIZE: int = 2048


async def execute(
    request: EmbeddingRequest,
    repository: EmbeddingApiRepository,
) -> CreateEmbeddingResponse:
    if request.model not in settings.SUPPORTED_EMBEDDING_MODELS:
        raise error_responses.UnsupportedModelError(model_name=request.model)
    if not request.input:
        raise error_responses.ValidationTypeError("Input must not be empty")

    input_texts = await _get_input_texts(request)
    if len(input_texts) > MAX_BATCH_SIZE:
        raise error_responses.ValidationTypeError(
            f"Maximum input array size for embeddings is {MAX_BATCH_SIZE}"
        )
    return await _get_embedding_result(input_texts, request.encoding_format, repository)


async def _get_input_texts(
    request: EmbeddingRequest,
) -> Union[List[str], List[List[int]]]:
    input_texts = request.input

    if not isinstance(input_texts, list):
        input_texts = [input_texts]
    elif all(isinstance(i, int) for i in input_texts):
        # If it's a List[int], convert it to List[List[int]] by wrapping it in another list
        input_texts = [input_texts]
    elif isinstance(input_texts[0], list) and all(
        isinstance(i, int) for sublist in input_texts for i in sublist
    ):
        # It's already a List[List[int]], so we leave it as is
        pass
    elif not all(isinstance(i, str) for i in input_texts):
        raise ValueError("Invalid input format: Expected List[str] or List[List[int]]")

    if not all(i for i in input_texts):
        raise error_responses.ValidationTypeError("All inputs must not be empty")
    return input_texts


async def _get_embedding_result(
    input_texts: Union[List[str], List[List[int]]],
    encoding_format: Optional[Literal["float", "base64"]],
    repository: EmbeddingApiRepository,
) -> CreateEmbeddingResponse:
    try:
        embeddings = await create_embeddings_use_case.execute(
            input_texts, encoding_format, repository
        )
    except EmbeddingApiError as exc:
        raise error_responses.EmbeddingError(exc.status, exc.message)
    except Exception as _:
        raise error_responses.InternalServerAPIError()
    return embeddings
