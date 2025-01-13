from enum import Enum
from dataclasses import dataclass


class TEEStatus(str, Enum):
    RUNNING = "RUNNING"
    TERMINATING = "TERMINATING"


@dataclass
class TEE:
    name: str
    cid: str
    status: TEEStatus
