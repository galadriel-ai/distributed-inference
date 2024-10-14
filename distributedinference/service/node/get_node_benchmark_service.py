from typing import Optional

from distributedinference.domain.node.entities import NodeBenchmark
from distributedinference.domain.node.entities import NodeInfo
from distributedinference.domain.user.entities import User
from distributedinference.repository.benchmark_repository import BenchmarkRepository
from distributedinference.service import error_responses
from distributedinference.service.node.entities import GetNodeBenchmarkResponse


async def execute(
    user: User,
    node_info: NodeInfo,
    model_name: str,
    repository: BenchmarkRepository,
) -> GetNodeBenchmarkResponse:
    node_benchmark: Optional[NodeBenchmark] = await repository.get_node_benchmark(
        user.uid, node_info.node_id, model_name
    )
    if not node_benchmark:
        raise error_responses.NotFoundAPIError()
    return GetNodeBenchmarkResponse(
        node_id=str(node_benchmark.node_id),
        model_name=node_benchmark.model_name,
        tokens_per_second=round(node_benchmark.benchmark_tokens_per_second, 2),
    )
