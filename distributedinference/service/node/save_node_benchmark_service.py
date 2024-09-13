from uuid import UUID

from distributedinference.domain.node.entities import NodeBenchmark
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.service.node import node_service_utils
from distributedinference.service.node.entities import PostNodeBenchmarkRequest
from distributedinference.service.node.entities import PostNodeBenchmarkResponse


async def execute(
    request: PostNodeBenchmarkRequest,
    user_profile_id: UUID,
    repository: NodeRepository,
) -> PostNodeBenchmarkResponse:
    # TODO: validate if tokens_per_second is enough
    node_uid = node_service_utils.parse_node_uid(request.node_id)
    node_benchmark = NodeBenchmark(
        node_id=node_uid,
        model_name=request.model_name,
        tokens_per_second=round(request.tokens_per_second, 2),
    )
    await repository.save_node_benchmark(user_profile_id, node_benchmark)

    return PostNodeBenchmarkResponse(
        model_name=node_benchmark.model_name,
        tokens_per_second=round(node_benchmark.tokens_per_second, 2),
    )
