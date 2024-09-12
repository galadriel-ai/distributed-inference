import time
from datetime import datetime
from datetime import timezone
from uuid import UUID

from uuid_extensions import uuid7


# DB inserts cannot be timezone aware..
def utcnow() -> datetime:
    utc = datetime.now(timezone.utc)
    utc_without_tz = utc.replace(tzinfo=None)
    return utc_without_tz


def historic_uuid(hours_back: int) -> UUID:
    return uuid7(time.time_ns() - (hours_back * 60 * 60 * 10**9))
