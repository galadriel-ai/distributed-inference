from typing import Optional

from distributedinference.domain.node.entities import NodeBenchmark
from distributedinference.domain.user.entities import User
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.service import error_responses
from distributedinference.service.node import node_service_utils
from distributedinference.service.node.entities import GetNodeBenchmarkResponse


async def execute(
    user: User,
    node_id: str,
    model_name: str,
    repository: NodeRepository,
) -> GetNodeBenchmarkResponse:
    node_uid = node_service_utils.parse_node_uid(node_id)
    node_benchmark: Optional[NodeBenchmark] = await repository.get_node_benchmark(
        user.uid, node_uid, model_name
    )
    if not node_benchmark:
        raise error_responses.NotFoundAPIError()
    return GetNodeBenchmarkResponse(
        node_id=str(node_benchmark.node_id),
        model_name=node_benchmark.model_name,
        tokens_per_second=round(node_benchmark.tokens_per_second, 2),
    )
