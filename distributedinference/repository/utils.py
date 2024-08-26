from datetime import datetime
from datetime import timezone


# DB inserts cannot be timezone aware..
def utcnow() -> datetime:
    utc = datetime.now(timezone.utc)
    utc_without_tz = utc.replace(tzinfo=None)
    return utc_without_tz
