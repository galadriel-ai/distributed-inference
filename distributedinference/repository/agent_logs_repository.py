from typing import List
from uuid import UUID

import sqlalchemy
from uuid_extensions import uuid7

from distributedinference.domain.agent.entities import AgentLogInput
from distributedinference.domain.agent.entities import AgentLogOutput
from distributedinference.domain.agent.entities import GetAgentLogsInput
from distributedinference.repository import utils
from distributedinference.repository.connection import SessionProvider
from distributedinference.repository.utils import historic_uuid_seconds

SQL_ADD = """
INSERT INTO agent_logs (
    id,
    agent_id,
    agent_instance_id,
    text,
    level,
    log_created_at,
    created_at,
    last_updated_at
) VALUES (
    :id,
    :agent_id,
    :text,
    :level,
    :log_created_at,
    :created_at,
    :last_updated_at
);
"""

SQL_GET = """
SELECT
    id,
    text,
    level,
    log_created_at
FROM agent_logs
WHERE 
    id < :cursor 
    AND agent_id = :agent_id
    AND level = ANY(:levels)
ORDER BY id DESC
LIMIT :limit;
"""

SQL_GET_COUNT_BY_TIME_AND_AGENT_ID = """
SELECT
    count(*) AS count
FROM
    agent_logs
WHERE
    agent_id = :agent_id
    AND id > :start_id;
"""


class AgentLogsRepository:

    def __init__(
        self, session_provider: SessionProvider, session_provider_read: SessionProvider
    ):
        self._session_provider = session_provider
        self._session_provider_read = session_provider_read

    async def add(
        self,
        agent_logs: AgentLogInput,
    ) -> None:
        created_at = utils.utcnow()
        data = [
            {
                "id": uuid7(),
                "agent_id": agent_logs.agent_id,
                "agent_instance_id": agent_logs.agent_instance_id,
                "text": log.text,
                "level": log.level,
                "log_created_at": utils.utc_from_timestamp(log.timestamp),
                "created_at": created_at,
                "last_updated_at": created_at,
            }
            for log in agent_logs.logs
        ]
        async with self._session_provider.get() as session:
            await session.execute(sqlalchemy.text(SQL_ADD), data)
            await session.commit()

    async def get(self, request: GetAgentLogsInput) -> List[AgentLogOutput]:
        data = {
            "agent_id": request.agent_id,
            "limit": request.limit,
            "levels": request.levels,
            "cursor": (
                str(request.cursor)
                if request.cursor
                else "ffffffff-ffff-ffff-ffff-ffffffffffff"
            ),
        }
        result = []
        async with self._session_provider_read.get() as session:
            rows = await session.execute(sqlalchemy.text(SQL_GET), data)
            for row in rows:
                result.append(
                    AgentLogOutput(
                        id=row.id,
                        text=row.text,
                        level=row.level,
                        timestamp=int(row.log_created_at.timestamp()),
                    )
                )
        return result

    async def get_count_by_agent(self, agent_id: UUID, seconds: int = 60) -> int:
        data = {
            "agent_id": agent_id,
            "start_id": historic_uuid_seconds(seconds),
        }
        async with self._session_provider_read.get() as session:
            result = await session.execute(
                sqlalchemy.text(SQL_GET_COUNT_BY_TIME_AND_AGENT_ID),
                data,
            )
            row = result.first()
            if row:
                return row.count  # type: ignore
        return 0
