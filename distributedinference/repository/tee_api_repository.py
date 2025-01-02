from typing import Dict
from typing import Optional
from urllib.parse import urljoin

import aiohttp

from distributedinference import api_logger
from distributedinference.utils.timer import async_timer

logger = api_logger.get()


class TeeApiRepository:

    def __init__(self, api_base_url: str, api_base_url_2: Optional[str], api_key: str):
        self.api_base_urls = [api_base_url]
        if api_base_url_2:
            self.api_base_urls.append(api_base_url_2)
        self.api_key = api_key

    @async_timer("tee_api_repository.completions", logger=logger)
    async def completions(self, api_key: Optional[str], request: Dict) -> Optional[Dict]:
        for api_base_url in self.api_base_urls:
            connected = await self._connectivity(api_base_url)
            if not connected:
                logger.error(f"TEE API not connected: {api_base_url}")
                continue
            # Use the user's API key if provided, otherwise use the default API key
            return await self._completions(request, api_key or self.api_key, api_base_url)
        return None

    @async_timer("tee_api_repository._connectivity", logger=logger)
    async def _connectivity(self, api_base_url: str) -> bool:
        """
        :return: Dict response,
        """
        try:
            timeout = aiohttp.ClientTimeout(total=5)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                response = await session.get(
                    urljoin(api_base_url, "v1/connectivity"),
                )
                if response.status != 200:
                    return False
                response_json = await response.json()
                return response_json.get("openai", False)
        except Exception:
            logger.error("Tee connectivity error", exc_info=True)
            return False

    @async_timer("tee_api_repository._completions", logger=logger)
    async def _completions(self, request: Dict, api_key: str, api_base_url: str) -> Optional[Dict]:
        """
        :param request: Dict so it is formatted as little as possible
        :return: Dict response, again to have as little formatting on it as possible
        """
        try:
            timeout = aiohttp.ClientTimeout(total=60)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                response = await session.post(
                    urljoin(api_base_url, "v1/chat/completions"),
                    headers={"Authorization": f"Bearer {api_key}"},
                    json=request,
                )
                if response.status != 200:
                    return None
                response_json = await response.json()
                return response_json
        except Exception:
            logger.error("Tee API error", exc_info=True)
            return None
