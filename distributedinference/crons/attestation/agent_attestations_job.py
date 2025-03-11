import base64
from typing import Optional
from typing import Tuple

import cbor2
from cryptography.hazmat.backends import default_backend
from cryptography.x509 import load_der_x509_certificate

from distributedinference.domain.agent.entities import AgentInstance
from distributedinference.domain.agent.entities import AttestationDetails
from distributedinference.repository.agent_repository import AgentRepository
from distributedinference.repository.tee_orchestration_repository import TeeOrchestrationRepository


async def execute(
    repo: AgentRepository,
    tee_repo: TeeOrchestrationRepository,
) -> None:
    agent_instances = await repo.get_agent_instances(is_deleted=False)
    for agent_instance in agent_instances:
        is_new_attestation_required, is_pcr0_required = await _get_requirements(agent_instance, repo)
        if not is_new_attestation_required and not is_pcr0_required:
            continue
        attestation_content = await _get_attestation(agent_instance, tee_repo)
        if attestation_content:
            attestation_details = await _get_attestation_details(attestation_content)
            if attestation_details:
                if is_pcr0_required:
                    await repo.insert_agent_instance_pcr0(
                        agent_instance.id, attestation_details.pcr0
                    )
                if is_new_attestation_required:
                    await repo.insert_attestation(
                        agent_instance.id, attestation_details
                    )


async def _get_requirements(agent_instance: AgentInstance, repo: AgentRepository) -> Tuple[bool, bool]:
    is_new_attestation_required = False
    is_pcr0_required = False
    if not agent_instance.pcr0:
        is_new_attestation_required = True
        is_pcr0_required = True
    else:
        existing_attestations = await repo.get_agent_attestations(agent_instance.id)
        if not existing_attestations:
            is_new_attestation_required = True
    return is_new_attestation_required, is_pcr0_required


async def _get_attestation(
    agent_instance: AgentInstance,
    tee_repo: TeeOrchestrationRepository,
) -> Optional[str]:
    attestation_content = await tee_repo.get_attestation(agent_instance.tee_host_base_url, agent_instance.id)
    return attestation_content


async def _get_attestation_details(
    attestation_content: str,
) -> Optional[AttestationDetails]:
    # Try catch?
    attestation_doc = base64.b64decode(attestation_content)
    data = cbor2.loads(attestation_doc)
    doc = data[2]
    doc_obj = cbor2.loads(doc)
    document_pcrs_arr = doc_obj["pcrs"]
    if not document_pcrs_arr:
        return None
    pcr0 = document_pcrs_arr[0].hex()

    cert = load_der_x509_certificate(
        doc_obj["certificate"], default_backend()
    )
    return AttestationDetails(
        attestation=attestation_content,
        valid_from=cert.not_valid_before_utc,
        valid_to=cert.not_valid_after_utc,
        pcr0=pcr0,
    )
