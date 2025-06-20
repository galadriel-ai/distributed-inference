from typing import Any
from typing import Optional

from starlette.requests import Request

from distributedinference.service.middleware.entitites import RequestStateKey


# pylint: disable=C2801
def set_state(request: Request, state_key: RequestStateKey, value: Any):
    request.state.__setattr__(state_key.value, value)


def get_state(request: Request, state_key: RequestStateKey) -> Optional[Any]:
    return getattr(request.state, state_key.value, None)
