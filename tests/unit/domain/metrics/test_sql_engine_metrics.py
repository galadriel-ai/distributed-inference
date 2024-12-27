from unittest.mock import MagicMock

import settings
from distributedinference.domain.metrics import sql_engine_metrics

DB_HOST_VALUE = None
DB_HOST_READ_VALUE = None

mock_engine_write = MagicMock()
mock_engine_write.engine.pool.status.return_value = "Pool size: 50  Connections in pool: 49 Current Overflow: -5 Current Checked out connections: 12"
mock_engine_read = MagicMock()
mock_engine_read.engine.pool.status.return_value = "Pool size: 51  Connections in pool: 50 Current Overflow: 6 Current Checked out connections: 13"
db_session_provider = {"write": mock_engine_write, "read": mock_engine_read}


def setup_function():
    global DB_HOST_VALUE
    global DB_HOST_READ_VALUE
    DB_HOST_VALUE = settings.DB_HOST
    DB_HOST_READ_VALUE = settings.DB_HOST_READ
    settings.DB_HOST = "db_host"
    settings.DB_HOST_READ = "db_host_read"


def teardown_function():
    settings.DB_HOST = DB_HOST_VALUE
    settings.DB_HOST_READ = DB_HOST_READ_VALUE


async def test_sql_engine_pool_size():
    await sql_engine_metrics.execute(db_session_provider)
    value = sql_engine_metrics.sql_engine_pool_size.collect()[0].samples[0].value
    assert value == 50
    value = sql_engine_metrics.sql_engine_pool_size.collect()[0].samples[1].value
    assert value == 51


async def test_sql_engine_connections_in_pool():
    await sql_engine_metrics.execute(db_session_provider)
    value = (
        sql_engine_metrics.sql_engine_connections_in_pool.collect()[0].samples[0].value
    )
    assert value == 49
    value = (
        sql_engine_metrics.sql_engine_connections_in_pool.collect()[0].samples[1].value
    )
    assert value == 50


async def test_sql_engine_current_overflow():
    await sql_engine_metrics.execute(db_session_provider)
    value = sql_engine_metrics.sql_engine_current_overflow.collect()[0].samples[0].value
    assert value == -5
    value = sql_engine_metrics.sql_engine_current_overflow.collect()[0].samples[1].value
    assert value == 6


async def test_sql_engine_checked_out_connections():
    await sql_engine_metrics.execute(db_session_provider)
    value = (
        sql_engine_metrics.sql_engine_checked_out_connections.collect()[0]
        .samples[0]
        .value
    )
    assert value == 12
    value = (
        sql_engine_metrics.sql_engine_checked_out_connections.collect()[0]
        .samples[1]
        .value
    )
    assert value == 13
