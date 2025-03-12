import base64
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from typing import Optional

import cbor2
from cryptography.hazmat.backends import default_backend
from cryptography.x509 import load_der_x509_certificate

from distributedinference import api_logger
from distributedinference.domain.agent.entities import AgentInstance
from distributedinference.domain.agent.entities import Attestation
from distributedinference.domain.agent.entities import AttestationDetails
from distributedinference.repository.agent_repository import AgentRepository
from distributedinference.repository.tee_orchestration_repository import (
    TeeOrchestrationRepository,
)

logger = api_logger.get()

# How many minutes before current attestation expires to get a new one
ATTESTATIONS_OVERLAP_MINUTES = 20


async def execute(
    repo: AgentRepository,
    tee_repo: TeeOrchestrationRepository,
) -> None:
    agent_instances = await repo.get_agent_instances(is_deleted=False)
    for agent_instance in agent_instances:
        try:
            await _update_attestation(
                agent_instance,
                repo,
                tee_repo,
            )
        except Exception:
            logger.error(
                f"Failed update attestation for agent instance: {agent_instance.id}",
                exc_info=True,
            )


async def _update_attestation(
    agent_instance: AgentInstance,
    repo: AgentRepository,
    tee_repo: TeeOrchestrationRepository,
) -> None:
    latest_attestation = await _get_latest_attestation(agent_instance, repo)
    if (
        agent_instance.pcr0
        and latest_attestation
        and _is_last_attestation_valid(latest_attestation)
    ):
        return None
    attestation_details = await _get_attestation(
        agent_instance, latest_attestation, tee_repo
    )
    if not attestation_details:
        logger.info(
            f"Failed to get new attestation for agenst instance: {agent_instance.id}"
        )
        return None

    if not agent_instance.pcr0:
        await repo.insert_agent_instance_pcr0(
            agent_instance.id, attestation_details.pcr0
        )
        logger.info(f"Added pcr0 for agent instance: {agent_instance.id}")
    if not latest_attestation:
        await repo.insert_attestation(agent_instance.id, attestation_details)
        logger.info(f"Added a new attestation for agent instance: {agent_instance.id}")


async def _get_latest_attestation(
    agent_instance: AgentInstance, repo: AgentRepository
) -> Optional[Attestation]:
    existing_attestations = await repo.get_agent_attestations(agent_instance.id)
    if not existing_attestations:
        return None
    return existing_attestations[-1]


def _is_last_attestation_valid(latest_attestation: Attestation) -> bool:
    current_time = datetime.now(timezone.utc)
    valid_from_utc = latest_attestation.valid_from.astimezone(timezone.utc)
    valid_to_utc = latest_attestation.valid_to.astimezone(timezone.utc) - timedelta(
        minutes=ATTESTATIONS_OVERLAP_MINUTES
    )
    if valid_from_utc < current_time < valid_to_utc:
        return True
    return False


async def _get_attestation(
    agent_instance: AgentInstance,
    latest_attestation: Optional[Attestation],
    tee_repo: TeeOrchestrationRepository,
) -> Optional[AttestationDetails]:
    attestation_content = await _get_raw_attestation(agent_instance, tee_repo)
    if not attestation_content:
        return None
    return await _get_attestation_details(attestation_content, latest_attestation)


async def _get_raw_attestation(
    agent_instance: AgentInstance,
    tee_repo: TeeOrchestrationRepository,
) -> Optional[str]:
    return await tee_repo.get_attestation(
        agent_instance.tee_host_base_url, agent_instance.id
    )


async def _get_attestation_details(
    attestation_content: str,
    latest_attestation: Optional[Attestation],
) -> Optional[AttestationDetails]:
    attestation_doc = base64.b64decode(attestation_content)
    data = cbor2.loads(attestation_doc)
    doc = data[2]
    doc_obj = cbor2.loads(doc)
    document_pcrs_arr = doc_obj["pcrs"]
    if not document_pcrs_arr:
        return None
    pcr0 = document_pcrs_arr[0].hex()

    cert = load_der_x509_certificate(doc_obj["certificate"], default_backend())

    valid_from = cert.not_valid_before_utc
    valid_to = cert.not_valid_after_utc
    if latest_attestation:
        if valid_to <= latest_attestation.valid_to.astimezone(timezone.utc):
            # No need for a newer one
            return None
        if attestation_content == latest_attestation.attestation:
            return None
    return AttestationDetails(
        attestation=attestation_content,
        valid_from=valid_from,
        valid_to=valid_to,
        pcr0=pcr0,
    )
