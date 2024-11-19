from dataclasses import dataclass

from prometheus_client import Gauge
from sqlalchemy.ext.asyncio import AsyncEngine

import settings
from distributedinference import api_logger
from distributedinference.repository import connection

sql_engine_pool_size = Gauge(
    "sql_engine_pool_size", "SQL engine pool size", ["postgres_ip"]
)
sql_engine_connections_in_pool = Gauge(
    "sql_engine_connections_in_pool", "SQL engine connections in pool", ["postgres_ip"]
)
sql_engine_current_overflow = Gauge(
    "sql_engine_current_overflow", "SQL engine current overflow", ["postgres_ip"]
)
sql_engine_checked_out_connections = Gauge(
    "sql_engine_checked_out_connections",
    "SQL engine checked out connections",
    ["postgres_ip"],
)

logger = api_logger.get()

a: str = 0

@dataclass
class SqlStatus:
    pool_size: float
    connections_in_pool: float
    current_overflow: float
    checked_out_connections: float


async def execute():
    clear()

    engine: AsyncEngine = connection.connection["engine"]
    set_values(engine, settings.DB_HOST)

    engine: AsyncEngine = connection.connection_read["engine"]
    set_values(engine, settings.DB_HOST_READ)


def set_values(engine: AsyncEngine, db_host: str):
    status = engine.pool.status()
    logger.info(f"SQL Engine Pool Raw Status: {status}")
    parsed_status = _parse_engine_pool_status(status)

    sql_engine_pool_size.labels(db_host).set(parsed_status.pool_size)
    sql_engine_connections_in_pool.labels(db_host).set(
        parsed_status.connections_in_pool
    )
    sql_engine_current_overflow.labels(db_host).set(parsed_status.current_overflow)
    sql_engine_checked_out_connections.labels(db_host).set(
        parsed_status.checked_out_connections
    )


def clear():
    sql_engine_pool_size.clear()
    sql_engine_connections_in_pool.clear()
    sql_engine_current_overflow.clear()
    sql_engine_checked_out_connections.clear()


def _parse_engine_pool_status(status: str) -> SqlStatus:
    return SqlStatus(
        pool_size=_parse(status, "Pool size: "),
        connections_in_pool=_parse(status, "Connections in pool: "),
        current_overflow=_parse(status, "Current Overflow: "),
        checked_out_connections=_parse(status, "Current Checked out connections: "),
    )


def _parse(status: str, name: str) -> float:
    try:
        return float(status.split(name)[1].split()[0])
    except:
        return float(0)
