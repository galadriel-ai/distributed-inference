import time
from datetime import date
from datetime import datetime
from datetime import timezone
from typing import Optional
from uuid import UUID

from uuid_extensions import uuid7


# DB inserts cannot be timezone aware..
def utcnow() -> datetime:
    utc = datetime.now(timezone.utc)
    utc_without_tz = utc.replace(tzinfo=None)
    return utc_without_tz


def utctoday() -> date:
    return datetime.now(timezone.utc).date()


def utc_from_timestamp(timestamp: int) -> datetime:
    utc = datetime.fromtimestamp(timestamp, timezone.utc)
    utc_without_tz = utc.replace(tzinfo=None)
    return utc_without_tz


def historic_uuid(hours_back: int) -> UUID:
    return uuid7(time.time_ns() - (hours_back * 60 * 60 * 10**9))


def historic_uuid_seconds(seconds: int) -> UUID:
    return uuid7(time.time_ns() - (seconds * 10**9))


def parse_int(value: Optional[int]) -> int:
    if value:
        return value
    return 0


def parse_float(value: Optional[float]) -> float:
    if value:
        return value
    return 0.0
