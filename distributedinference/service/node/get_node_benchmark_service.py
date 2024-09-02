from typing import Optional

from distributedinference.domain.node.entities import NodeBenchmark
from distributedinference.domain.user.entities import User
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.service import error_responses
from distributedinference.service.node.entities import GetNodeBenchmarkResponse


async def execute(
    user: User,
    model_name: str,
    repository: NodeRepository,
) -> GetNodeBenchmarkResponse:
    node_benchmark: Optional[NodeBenchmark] = await repository.get_node_benchmark(
        user.uid, model_name
    )
    if not node_benchmark:
        raise error_responses.NotFoundAPIError()
    return GetNodeBenchmarkResponse(
        model_name=node_benchmark.model_name,
        tokens_per_second=round(node_benchmark.tokens_per_second, 2),
    )
