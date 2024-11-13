from typing import List

from distributedinference.repository.embedding_api_repository import (
    EmbeddingApiRepository,
)


async def execute(
    inputs: List[str], embedding_repository: EmbeddingApiRepository
) -> List[List[float]]:
    return await embedding_repository.create_embeddings(inputs)
