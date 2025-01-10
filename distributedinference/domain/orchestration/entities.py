from uuid import UUID
from dataclasses import dataclass


@dataclass
class TEE:
    enclave_name: str
    enclave_cid: str
