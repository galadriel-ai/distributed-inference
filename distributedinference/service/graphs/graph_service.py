from distributedinference.repository.grafana_api_repository import GrafanaApiRepository
from distributedinference.service.graphs.entities import GetGraphResponse


async def execute(repo: GrafanaApiRepository) -> GetGraphResponse:
    graph = await repo.get_network_inferences()
    return GetGraphResponse(
        timestamps=[g.timestamp for g in graph],
        values=[g.value for g in graph],
    )
