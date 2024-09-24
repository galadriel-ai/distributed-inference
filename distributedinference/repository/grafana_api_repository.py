import datetime
from dataclasses import dataclass
from typing import List
from urllib.parse import urljoin

import aiohttp
from aiocache import SimpleMemoryCache
from aiocache import cached

from distributedinference import api_logger

CACHE_LENGTH_SECONDS = 600

PROM_INFERENCE_REQUESTS_PER_HOUR = "sum(increase(node_requests[1h]))"
# For 1 node_id
# 'sum(increase(node_requests{node_uid="066d84e8-e195-76f0-8000-ff76fcc77b19"}[1h]))'
# For multiple node_ids
# 'sum(increase(node_requests{node_uid=~"066d84e8-e195-76f0-8000-ff76fcc77b19|066d8706-081e-7013-8000-72c23af95cd3"}[1h]))'

logger = api_logger.get()


@dataclass
class GraphValue:
    timestamp: int
    value: int


class GrafanaApiRepository:
    REQUEST_TIMEOUT_SECONDS = 30

    def __init__(self, api_base_url: str, api_key: str):
        self.api_base_url = api_base_url
        self.api_key = api_key

    async def get_network_inferences(self, hours: int = 24) -> List[GraphValue]:
        return await _get_cached_query_result(
            self.api_base_url,
            self.api_key,
            hours,
            PROM_INFERENCE_REQUESTS_PER_HOUR,
        )


@cached(ttl=CACHE_LENGTH_SECONDS, cache=SimpleMemoryCache)
async def _get_cached_query_result(
    api_base_url: str,
    api_key: str,
    hours: int,
    query: str,
) -> List[GraphValue]:
    try:
        end_timestamp = _get_latest_15min_mark()
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            response = await session.post(
                urljoin(api_base_url, "api/datasources/proxy/1/api/v1/query_range"),
                headers={"Authorization": f"Bearer {api_key}"},
                data={
                    "query": query,
                    "start": int(end_timestamp) - (hours * 60 * 60),
                    "end": end_timestamp,
                    "step": 3600,
                },
            )
        if response.status != 200:
            return []
        response_json = await response.json()
        values = response_json["data"]["result"][0]["values"]
        return [
            GraphValue(
                timestamp=v[0],
                value=int(float(v[1])),
            )
            for v in values
        ]
    except Exception:
        logger.error("Error querying grafana", exc_info=True)
        return []


def _get_latest_15min_mark() -> int:
    now = datetime.datetime.now(datetime.UTC)
    minutes_to_subtract = now.minute % 15
    latest_15min_mark = now - datetime.timedelta(
        minutes=minutes_to_subtract, seconds=now.second, microseconds=now.microsecond
    )
    return int(latest_15min_mark.timestamp())
