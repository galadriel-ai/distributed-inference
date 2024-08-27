import asyncio
from dataclasses import dataclass
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


@dataclass
class InferenceContent:
    type: str
    value: str


@dataclass
class InferenceMessage:
    role: str
    content: InferenceContent


@dataclass
class InferenceRequest:
    model: str
    messages: List[InferenceMessage]


@dataclass
class InferenceResponse:
    content: str
    finish_reason: Optional[str] = None
