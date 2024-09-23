from datetime import datetime
from uuid import UUID

from distributedinference.service import error_responses


def to_response_date_format(date: datetime) -> str:
    """
    Accepts datetimes with tz info and no tz info
    """
    return date.replace(tzinfo=None).replace(microsecond=0).isoformat() + "Z"


def parse_uuid(uid: str) -> UUID:
    try:
        return UUID(uid)
    except ValueError:
        raise error_responses.ValidationTypeError("Error, id is not a valid UUID")
    except TypeError:
        raise error_responses.ValidationTypeError("Error, id is not a valid type")
    except Exception:
        raise error_responses.ValidationTypeError("Failed to process id")
