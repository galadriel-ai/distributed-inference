from unittest.mock import AsyncMock
from uuid import UUID

from distributedinference.domain.node.entities import NodeInfo
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.service.node import update_node_service as service
from distributedinference.service.node.entities import UpdateNodeRequest
from distributedinference.service.node.entities import UpdateNodeResponse


def _get_node_info():
    return NodeInfo(
        node_id=UUID("06720980-3d82-784d-8000-3150ecf8faed"),
        name="name",
        name_alias="alias",
    )


async def test_no_updates():
    repo = AsyncMock(spec=NodeRepository)
    response = await service.execute(
        UpdateNodeRequest(
            node_id="node-id",
            node_name=None,
            is_archived=None,
        ),
        _get_node_info(),
        repo,
    )
    assert response == UpdateNodeResponse(
        is_name_updated=False,
        is_archival_status_updated=False,
    )


async def test_update_name():
    repo = AsyncMock(spec=NodeRepository)
    response = await service.execute(
        UpdateNodeRequest(
            node_id="node-id",
            node_name="name",
            is_archived=None,
        ),
        _get_node_info(),
        repo,
    )
    assert response == UpdateNodeResponse(
        is_name_updated=True,
        is_archival_status_updated=False,
    )


async def test_update_archival():
    repo = AsyncMock(spec=NodeRepository)
    response = await service.execute(
        UpdateNodeRequest(
            node_id="node-id",
            node_name=None,
            is_archived=True,
        ),
        _get_node_info(),
        repo,
    )
    assert response == UpdateNodeResponse(
        is_name_updated=False,
        is_archival_status_updated=True,
    )


async def test_update_name_and_archival():
    repo = AsyncMock(spec=NodeRepository)
    response = await service.execute(
        UpdateNodeRequest(
            node_id="node-id",
            node_name="name",
            is_archived=True,
        ),
        _get_node_info(),
        repo,
    )
    assert response == UpdateNodeResponse(
        is_name_updated=True,
        is_archival_status_updated=True,
    )
