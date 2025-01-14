from typing import Any
from typing import Dict
from typing import List
from typing import Optional

import httpx

from distributedinference import api_logger
from distributedinference.utils.timer import async_timer
from distributedinference.domain.orchestration.entities import TEE
from distributedinference.domain.orchestration.entities import TEEStatus

logger = api_logger.get()


class TeeOrchestrationRepository:

    def __init__(self, tee_host_url: str):
        self.base_url = tee_host_url

    # pylint: disable=W0613
    @async_timer("tee_repository.create_tee", logger=logger)
    async def create_tee(
        self, tee_name: str, docker_hub_image: str, env_vars: Dict[str, Any]
    ) -> TEE:
        data = {
            "enclave_name": tee_name,
            "docker_hub_image": docker_hub_image,
            "env_vars": env_vars,
        }
        response = await self._post("tee/deploy", data)
        enclave_cid = response["result"]["EnclaveCID"]
        return TEE(name=tee_name, cid=enclave_cid, status=TEEStatus.RUNNING)

    @async_timer("tee_repository.get_all_tees", logger=logger)
    async def get_all_tees(
        self,
    ) -> List[TEE]:
        tees = []
        response = await self._get("tee/enclaves")
        for tee in response.get("enclaves", []):
            tees.append(
                TEE(
                    name=tee["enclave_name"],
                    cid=tee["enclave_cid"],
                    status=TEEStatus(tee["enclave_status"]),
                )
            )
        return tees

    @async_timer("tee_repository.delete_tee", logger=logger)
    async def delete_tee(self, tee_name: str) -> bool:
        data = {
            "enclave_name": tee_name,
        }
        response = await self._post("tee/terminate", data)
        return response.get("Terminated", False)

    async def _post(self, url: str, data: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(self.base_url + url, json=data)
            response.raise_for_status()
            data = response.json()
        return data

    async def _get(
        self, url: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.get(self.base_url + url, params=params)
            response.raise_for_status()
            data = response.json()
        return data
