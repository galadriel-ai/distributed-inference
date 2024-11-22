from uuid import UUID

from distributedinference.domain.node.entities import FullNodeInfo
from distributedinference.domain.node.entities import NodeBenchmark
from distributedinference.repository.benchmark_repository import BenchmarkRepository
from distributedinference.service.node.entities import PostNodeBenchmarkRequest
from distributedinference.service.node.entities import PostNodeBenchmarkResponse


async def execute(
    request: PostNodeBenchmarkRequest,
    node_info: FullNodeInfo,
    user_profile_id: UUID,
    repository: BenchmarkRepository,
) -> PostNodeBenchmarkResponse:
    node_benchmark = NodeBenchmark(
        node_id=node_info.node_id,
        model_name=request.model_name,
        benchmark_tokens_per_second=round(request.tokens_per_second, 2),
        gpu_model=node_info.specs.gpu_model,
        gpu_count=node_info.specs.gpu_count,
    )
    await repository.save_node_benchmark(user_profile_id, node_benchmark)

    return PostNodeBenchmarkResponse()
