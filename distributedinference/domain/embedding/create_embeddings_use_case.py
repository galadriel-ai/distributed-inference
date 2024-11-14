from typing import List
from typing import Literal
from typing import Optional
from typing import Union

from openai.types import CreateEmbeddingResponse

from distributedinference.repository.embedding_api_repository import (
    EmbeddingApiRepository,
)


async def execute(
    inputs: Union[List[str], List[List[int]]],
    encoding_format: Optional[Literal["float", "base64"]],
    embedding_repository: EmbeddingApiRepository,
) -> CreateEmbeddingResponse:
    return await embedding_repository.create_embeddings(inputs, encoding_format)
