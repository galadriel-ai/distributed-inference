from unittest.mock import AsyncMock

import pytest

import settings
from distributedinference.domain.embedding.entities import EmbeddingApiError
from distributedinference.repository.embedding_api_repository import (
    EmbeddingApiRepository,
)
from distributedinference.service import error_responses
from distributedinference.service.embedding import embedding_service as service
from distributedinference.service.embedding.entities import EmbeddingObject
from distributedinference.service.embedding.entities import EmbeddingRequest
from distributedinference.service.embedding.entities import EmbeddingResponse


async def test_success():
    service.create_embeddings_use_case = AsyncMock()
    service.create_embeddings_use_case.execute.return_value = [
        [1, 2, 3],
        [4, 5, 6],
    ]
    repo = AsyncMock(spec=EmbeddingApiRepository)
    repo.create_embeddings.return_value = [
        [1, 2, 3],
        [4, 5, 6],
    ]
    model = settings.SUPPORTED_EMBEDDING_MODELS[0]
    response = await service.execute(
        EmbeddingRequest(
            input=["asd", "fgh"],
            model=model,
        ),
        repository=repo,
    )
    assert response == EmbeddingResponse(
        object="list",
        data=[
            EmbeddingObject(
                index=0,
                embedding=[1, 2, 3],
                object="embedding",
            ),
            EmbeddingObject(
                index=1,
                embedding=[4, 5, 6],
                object="embedding",
            ),
        ],
        model=model,
    )
    service.create_embeddings_use_case.execute.assert_called_with(["asd", "fgh"], repo)


async def test_converts_to_list():
    service.create_embeddings_use_case = AsyncMock()
    service.create_embeddings_use_case.execute.return_value = [[1, 2, 3]]
    repo = AsyncMock(spec=EmbeddingApiRepository)
    repo.create_embeddings.return_value = [
        [1, 2, 3],
    ]
    model = settings.SUPPORTED_EMBEDDING_MODELS[0]
    response = await service.execute(
        EmbeddingRequest(
            input="asd",
            model=model,
        ),
        repository=repo,
    )
    assert response == EmbeddingResponse(
        object="list",
        data=[
            EmbeddingObject(
                index=0,
                embedding=[1, 2, 3],
                object="embedding",
            ),
        ],
        model=model,
    )
    service.create_embeddings_use_case.execute.assert_called_with(["asd"], repo)


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
