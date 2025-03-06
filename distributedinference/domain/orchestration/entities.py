from enum import Enum
from dataclasses import dataclass


class TEEStatus(str, Enum):
    RUNNING = "RUNNING"
    TERMINATING = "TERMINATING"


@dataclass
class TEE:
    name: str
    cid: str
    host_base_url: str
    status: TEEStatus
