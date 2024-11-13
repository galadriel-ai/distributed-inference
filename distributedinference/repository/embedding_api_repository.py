from typing import List
from urllib.parse import urljoin

import aiohttp

from distributedinference import api_logger
from distributedinference.domain.embedding.entities import EmbeddingApiError

logger = api_logger.get()


class EmbeddingApiRepository:

    def __init__(self, api_base_url: str):
        self.api_base_url = api_base_url

    async def create_embeddings(self, chunks: List[str]) -> List[List[float]]:
        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                response = await session.post(
                    urljoin(self.api_base_url, "/embed"),
                    headers={"Content-Type": "application/json"},
                    json={"inputs": chunks},
                )
                if response.status == 200:
                    response_json = await response.json()
                    if len(response_json) == len(chunks):
                        return response_json
                else:
                    raise EmbeddingApiError(response.status, response.reason)
        except EmbeddingApiError:
            raise
        except Exception as _:
            logger.error("Unexpected error on embeddings creation: ", exc_info=True)
            raise EmbeddingApiError(500, message=None)
        return []
