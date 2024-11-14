from unittest.mock import AsyncMock

import pytest
from openai.types import CreateEmbeddingResponse
from openai.types import Embedding
from openai.types.create_embedding_response import Usage

import settings
from distributedinference.domain.embedding.entities import EmbeddingApiError
from distributedinference.repository.embedding_api_repository import (
    EmbeddingApiRepository,
)
from distributedinference.service import error_responses
from distributedinference.service.embedding import embedding_service as service
from distributedinference.service.embedding.entities import EmbeddingRequest


def _get_default_response() -> CreateEmbeddingResponse:
    return CreateEmbeddingResponse(
        data=[
            Embedding(embedding=[1, 2, 3], index=0, object="embedding"),
            Embedding(embedding=[4, 5, 6], index=0, object="embedding"),
        ],
        model=settings.SUPPORTED_EMBEDDING_MODELS[0],
        object="list",
        usage=Usage(
            prompt_tokens=15,
            total_tokens=15,
        ),
    )


async def test_success():
    service.create_embeddings_use_case = AsyncMock()
    service.create_embeddings_use_case.execute.return_value = _get_default_response()
    repo = AsyncMock(spec=EmbeddingApiRepository)
    model = settings.SUPPORTED_EMBEDDING_MODELS[0]
    response = await service.execute(
        EmbeddingRequest(
            input=["asd", "fgh"],
            model=model,
        ),
        repository=repo,
    )
    assert response == _get_default_response()
    service.create_embeddings_use_case.execute.assert_called_with(
        ["asd", "fgh"], None, repo
    )


async def test_converts_to_list():
    service.create_embeddings_use_case = AsyncMock()
    service.create_embeddings_use_case.execute.return_value = _get_default_response()
    repo = AsyncMock(spec=EmbeddingApiRepository)
    model = settings.SUPPORTED_EMBEDDING_MODELS[0]
    response = await service.execute(
        EmbeddingRequest(input="asd", model=model, encoding_format="base64"),
        repository=repo,
    )
    assert response == _get_default_response()
    service.create_embeddings_use_case.execute.assert_called_with(
        ["asd"], "base64", repo
    )


async def test_converts_list_of_ints():
    service.create_embeddings_use_case = AsyncMock()
    service.create_embeddings_use_case.execute.return_value = _get_default_response()
    repo = AsyncMock(spec=EmbeddingApiRepository)
    model = settings.SUPPORTED_EMBEDDING_MODELS[0]
    response = await service.execute(
        EmbeddingRequest(input=[1, 2, 3], model=model, encoding_format="float"),
        repository=repo,
    )
    assert response == _get_default_response()
    service.create_embeddings_use_case.execute.assert_called_with(
        [[1, 2, 3]], "float", repo
    )


async def test_unsupported_model():
    repo = AsyncMock(spec=EmbeddingApiRepository)
    model = "random-model"
    with pytest.raises(error_responses.UnsupportedModelError) as e:
        await service.execute(
            EmbeddingRequest(
                input="asd",
                model=model,
            ),
            repository=repo,
        )
        assert e is not None


async def test_empty_input():
    repo = AsyncMock(spec=EmbeddingApiRepository)
    model = settings.SUPPORTED_EMBEDDING_MODELS[0]
    for i in ["", [], [[123, 33], []], ["", "asd"]]:
        with pytest.raises(error_responses.ValidationTypeError) as e:
            await service.execute(
                EmbeddingRequest(
                    input=i,
                    model=model,
                ),
                repository=repo,
            )
            assert e is not None


async def test_batch_size_exceeded_model():
    repo = AsyncMock(spec=EmbeddingApiRepository)
    model = settings.SUPPORTED_EMBEDDING_MODELS[0]
    with pytest.raises(error_responses.ValidationTypeError) as e:
        await service.execute(
            EmbeddingRequest(
                input=["a" for _ in range(service.MAX_BATCH_SIZE + 1)],
                model=model,
            ),
            repository=repo,
        )
        assert e is not None


async def test_embedding_error():
    def _error(*args, **kwargs):
        raise EmbeddingApiError(418, "I'm a teapot")

    repo = AsyncMock(spec=EmbeddingApiRepository)
    service.create_embeddings_use_case.execute = AsyncMock(side_effect=_error)
    model = settings.SUPPORTED_EMBEDDING_MODELS[0]
    with pytest.raises(error_responses.EmbeddingError) as e:
        await service.execute(
            EmbeddingRequest(
                input="asd",
                model=model,
            ),
            repository=repo,
        )
        assert "teapot" in e.message


async def test_embedding_unexpected_error():
    def _error(*args, **kwargs):
        raise Exception("ASDASD")

    repo = AsyncMock(spec=EmbeddingApiRepository)
    service.create_embeddings_use_case.execute = AsyncMock(side_effect=_error)
    model = settings.SUPPORTED_EMBEDDING_MODELS[0]
    with pytest.raises(error_responses.InternalServerAPIError) as e:
        await service.execute(
            EmbeddingRequest(
                input="asd",
                model=model,
            ),
            repository=repo,
        )
