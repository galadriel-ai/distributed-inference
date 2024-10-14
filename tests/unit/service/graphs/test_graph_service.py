from unittest.mock import AsyncMock

import pytest
from uuid import UUID

from uuid_extensions import uuid7

from distributedinference.domain.user.entities import User
from distributedinference.repository.grafana_api_repository import GrafanaApiRepository
from distributedinference.repository.grafana_api_repository import GraphValue
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.service import error_responses
from distributedinference.service.graphs import graph_service as service
from distributedinference.service.graphs.entities import GetGraphResponse


def _get_user():
    return User(
        uid=uuid7(),
        name="mock_name",
        email="mock_email",
        usage_tier_id=UUID("06706644-2409-7efd-8000-3371c5d632d3"),
    )


async def test_success_network():
    user = _get_user()
    grafana_repository = AsyncMock(spec=GrafanaApiRepository)
    grafana_repository.get_network_inferences.return_value = [
        GraphValue(
            timestamp=1,
            value=2,
        )
    ]
    node_repository = AsyncMock(spec=NodeRepository)

    result = await service.execute(
        "network", None, user, grafana_repository, node_repository
    )

    assert result == GetGraphResponse(
        timestamps=[1],
        values=[2],
    )


async def test_success_user():
    user = _get_user()
    grafana_repository = AsyncMock(spec=GrafanaApiRepository)
    grafana_repository.get_node_inferences.return_value = [
        GraphValue(
            timestamp=1,
            value=2,
        )
    ]
    node_repository = AsyncMock(spec=NodeRepository)
    node_repository.get_user_node_ids.return_value = [uuid7()]

    result = await service.execute(
        "user", None, user, grafana_repository, node_repository
    )

    assert result == GetGraphResponse(
        timestamps=[1],
        values=[2],
    )


async def test_success_node():
    user = _get_user()
    grafana_repository = AsyncMock(spec=GrafanaApiRepository)
    grafana_repository.get_node_inferences.return_value = [
        GraphValue(
            timestamp=1,
            value=2,
        )
    ]
    node_repository = AsyncMock(spec=NodeRepository)
    node_repository.get_user_node_id_by_name.return_value = uuid7()

    result = await service.execute(
        "node", "node-name", user, grafana_repository, node_repository
    )

    assert result == GetGraphResponse(
        timestamps=[1],
        values=[2],
    )


async def test_invalid_graph_type():
    user = _get_user()
    grafana_repository = AsyncMock(spec=GrafanaApiRepository)
    node_repository = AsyncMock(spec=NodeRepository)
    with pytest.raises(error_responses.NotFoundAPIError) as e:
        await service.execute(
            "random type", None, user, grafana_repository, node_repository
        )


async def test_invalid_node_name():
    user = _get_user()
    grafana_repository = AsyncMock(spec=GrafanaApiRepository)
    node_repository = AsyncMock(spec=NodeRepository)
    node_repository.get_user_node_id_by_name.return_value = None
    with pytest.raises(error_responses.NotFoundAPIError) as e:
        await service.execute(
            "node", "node-name", user, grafana_repository, node_repository
        )


async def test_missing_node_name():
    user = _get_user()
    grafana_repository = AsyncMock(spec=GrafanaApiRepository)
    node_repository = AsyncMock(spec=NodeRepository)
    node_repository.get_user_node_id_by_name.return_value = None
    with pytest.raises(error_responses.ValidationTypeError) as e:
        await service.execute("node", None, user, grafana_repository, node_repository)
