from datetime import datetime


def to_response_date_format(date: datetime) -> str:
    """
    Accepts datetimes with tz info and no tz info
    """
    return date.replace(tzinfo=None).replace(microsecond=0).isoformat() + "Z"
