from typing import List
from typing import Literal
from typing import Optional
from typing import Union

from openai import AsyncOpenAI
from openai.types import CreateEmbeddingResponse

from distributedinference.api_logger import api_logger

logger = api_logger.get()


class EmbeddingApiRepository:

    def __init__(self, api_base_url: str, model: str):
        self.model = model
        self.client = AsyncOpenAI(
            base_url=api_base_url,
            api_key="not-needed",
        )

    async def create_embeddings(
        self,
        chunks: Union[List[str], List[List[int]]],
        encoding_format: Optional[Literal["float", "base64"]],
    ) -> CreateEmbeddingResponse:
        return await self.client.embeddings.create(
            model=self.model, input=chunks, encoding_format=encoding_format or "float"
        )
