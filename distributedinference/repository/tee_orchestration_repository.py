from typing import Any
from typing import Dict
from typing import List

import httpx

from distributedinference import api_logger
from distributedinference.utils.timer import async_timer
from distributedinference.domain.orchestration.entities import TEE

logger = api_logger.get()


class TeeOrchestrationRepository:

    def __init__(self, tee_host_url: str):
        self.base_url = tee_host_url

    # pylint: disable=W0613
    @async_timer("tee_repository.create_tee_instance", logger=logger)
    async def create_tee(
        self, tee_name: str, docker_hub_image: str, env_vars: Dict[str, Any]
    ) -> TEE:
        data = {
            "enclave_name": tee_name,
            "docker_hub_image": docker_hub_image,
        }
        response = await self._post("tee/deploy", data)
        enclave_cid = response["result"]["EnclaveID"]
        return TEE(enclave_name=tee_name, enclave_cid=enclave_cid)

    @async_timer("tee_repository.completions", logger=logger)
    async def get_all_tees(
        self,
    ) -> List[TEE]:
        return [
            TEE(enclave_name="mock_name_1", enclave_cid="mock_cid_1"),
            TEE(enclave_name="mock_name_2", enclave_cid="mock_cid_2"),
            TEE(enclave_name="mock_name_3", enclave_cid="mock_cid_3"),
        ]

    async def _post(self, url: str, data: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(self.base_url + url, json=data)
            response.raise_for_status()
            data = response.json()
        return data
