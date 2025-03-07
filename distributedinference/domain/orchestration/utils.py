from distributedinference.domain.agent.entities import AgentInstance
from distributedinference.domain.orchestration.entities import TEE
from distributedinference.domain.orchestration.entities import TEEStatus


def agent_instance_to_tee(agent_instance: AgentInstance) -> TEE:
    return TEE(
        name=str(agent_instance.id),
        cid=agent_instance.enclave_cid,
        host_base_url=agent_instance.tee_host_base_url,
        # TODO: Get status from TEE orchestration?
        status=TEEStatus.RUNNING,
    )
