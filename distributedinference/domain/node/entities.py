import asyncio
from dataclasses import dataclass
from dataclasses_json import dataclass_json
from uuid import UUID
from typing import List
from typing import Optional

from fastapi import WebSocket


@dataclass(frozen=True)
class Node:
    uid: UUID
    model: str


@dataclass(frozen=True)
class ConnectedNode(Node):
    websocket: WebSocket
    message_queue: asyncio.Queue


@dataclass_json
@dataclass
class InferenceContent:
    type: str
    value: str


@dataclass_json
@dataclass
class InferenceMessage:
    role: str
    content: InferenceContent


@dataclass_json
@dataclass
class InferenceRequest:
    model: str
    messages: List[InferenceMessage]


@dataclass_json
@dataclass
class InferenceResponse:
    content: str
    finish_reason: Optional[str] = None
