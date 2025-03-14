from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from uuid import UUID

import httpx

from distributedinference import api_logger
from distributedinference.utils.timer import async_timer
from distributedinference.domain.orchestration.entities import TEE
from distributedinference.domain.orchestration.entities import TEEStatus
from distributedinference.domain.orchestration.exceptions import NoCapacityError

logger = api_logger.get()

MAXIMUM_TEE_COUNT_PER_HOST = 4
TIMEOUT = 240


class TeeOrchestrationRepository:

    def __init__(self, tee_host_urls: str):
        self.base_urls = tee_host_urls

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
        host_base_url = await self._get_host_with_free_capacity()
        if not host_base_url:
            raise NoCapacityError("No capacity to deploy TEE")
        response = await self._post(host_base_url, "tee/deploy", data)
        enclave_cid = response["result"]["EnclaveCID"]
        return TEE(
            name=tee_name,
            cid=enclave_cid,
            host_base_url=host_base_url,
            status=TEEStatus.RUNNING,
        )

    @async_timer("tee_repository.get_all_tees", logger=logger)
    async def get_all_tees(
        self,
    ) -> List[TEE]:
        tees = []
        for base_url in self.base_urls:
            tees.extend(await self._get_host_tees(base_url))
        return tees

    @async_timer("tee_repository._get_host_tees", logger=logger)
    async def _get_host_tees(self, host_base_url: str) -> List[TEE]:
        tees = []
        response = await self._get(host_base_url, "tee/enclaves")
        for tee in response.get("enclaves", []):
            tees.append(
                TEE(
                    name=tee["enclave_name"],
                    cid=tee["enclave_cid"],
                    host_base_url=host_base_url,
                    status=TEEStatus(tee["enclave_status"]),
                )
            )
        return tees

    @async_timer("tee_repository.get_attestation", logger=logger)
    async def get_attestation(
        self,
        host_base_url: str,
        agent_instance_id: UUID,
    ) -> Optional[str]:
        try:
            response = await self._get(
                host_base_url, f"tee/attestation/{agent_instance_id}"
            )
            if attestation := response.get("attestation"):
                return attestation
        except Exception:
            logger.error(
                f"Error getting attestation for agent instance: {agent_instance_id}",
                exc_info=True,
            )
        return None

    @async_timer("tee_repository._get_host_with_free_capacity", logger=logger)
    async def _get_host_with_free_capacity(self) -> Optional[str]:
        for base_url in self.base_urls:
            response = await self._get(base_url, "tee/enclaves")
            if len(response.get("enclaves", [])) < MAXIMUM_TEE_COUNT_PER_HOST:
                return base_url
        return None

    @async_timer("tee_repository.delete_tee", logger=logger)
    async def delete_tee(self, tee: TEE) -> bool:
        data = {
            "enclave_name": tee.name,
        }
        response = await self._post(tee.host_base_url, "tee/terminate", data)
        return response.get("Terminated", False)

    async def _post(
        self, base_url: str, url: str, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            try:
                response = await client.post(base_url + url, json=data)
                response.raise_for_status()
                data = response.json()
            except httpx.HTTPStatusError as e:
                try:
                    error_details = e.response.json().get(
                        "detail", "No detail provided"
                    )
                except Exception:
                    error_details = e.response.text  # Fallback to raw text if not JSON
                raise RuntimeError(error_details) from e
        return data

    async def _get(
        self, base_url: str, url: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            try:
                response = await client.get(base_url + url, params=params)
                response.raise_for_status()
                data = response.json()
            except httpx.HTTPStatusError as e:
                try:
                    error_details = e.response.json().get(
                        "detail", "No detail provided"
                    )
                except Exception:
                    error_details = e.response.text  # Fallback to raw text if not JSON
                raise RuntimeError(error_details) from e
        return data
