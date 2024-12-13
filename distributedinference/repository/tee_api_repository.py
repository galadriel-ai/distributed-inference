from typing import Dict
from typing import Optional
from urllib.parse import urljoin

import aiohttp

from distributedinference import api_logger

logger = api_logger.get()


class TeeApiRepository:

    def __init__(self, api_base_url: str, api_key: str):
        self.api_base_url = api_base_url
        self.api_key = api_key

    async def completions(self, request: Dict) -> Optional[Dict]:
        """
        :param request: Dict so it is formatted as little as possible
        :return: Dict response, again to have as little formatting on it as possible
        """
        try:
            timeout = aiohttp.ClientTimeout(total=60)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                response = await session.post(
                    urljoin(self.api_base_url, "v1/chat/completions"),
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json=request,
                )
                if response.status != 200:
                    return None
                response_json = await response.json()
                return response_json
        except Exception:
            logger.error("Tee API error", exc_info=True)
            return None
