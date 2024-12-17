from typing import Optional
from urllib.parse import urlencode
from urllib.parse import urljoin

import aiohttp
from duckduckgo_search import AsyncDDGS

import settings
from distributedinference.api_logger import api_logger
from distributedinference.service.tool.entities import SearchRequest
from distributedinference.service.tool.entities import SearchResponse

SERPAPI_BASE_URL = "https://serpapi.com/search"
SEARCH_TIMEOUT_SECONDS = 10

logger = api_logger.get()


async def execute(request: SearchRequest) -> SearchResponse:
    serpapi_results = await _search_serpapi(request)
    if serpapi_results:
        return serpapi_results
    ddg_results = await _search_ddg(request)
    return ddg_results or SearchResponse(results=[])


async def _search_serpapi(request: SearchRequest) -> Optional[SearchResponse]:
    params = {
        "engine": "google",
        "q": request.query,
        "num": request.max_results,
        "api_key": settings.SERPAPI_KEY,
    }
    try:
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            response = await session.get(
                urljoin(urljoin(SERPAPI_BASE_URL, "search"), f"?{urlencode(params)}"),
            )
        if response.status != 200:
            return None
        response_json = await response.json()
        if results := response_json.get("organic_results"):
            return SearchResponse(results=results)
    except:
        logger.error("Error searching serpAPI", exc_info=True)
    return None


async def _search_ddg(request: SearchRequest) -> Optional[SearchResponse]:
    try:
        results = await AsyncDDGS(
            proxy=None,
            timeout=SEARCH_TIMEOUT_SECONDS,
        ).atext(
            request.query,
            max_results=request.max_results,
        )
        return SearchResponse(results=results)
    except:
        logger.error("Error searching duckduckgo", exc_info=True)
    return None
