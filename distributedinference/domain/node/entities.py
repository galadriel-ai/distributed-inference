import asyncio
from dataclasses import dataclass
from typing import Dict
from typing import List
from uuid import UUID

from fastapi import WebSocket
from openai.types.chat import ChatCompletionChunk
from openai.types.chat import CompletionCreateParams


@dataclass(frozen=True)
class Node:
    uid: UUID
    model: str


@dataclass(frozen=True)
class ConnectedNode(Node):
    websocket: WebSocket
    request_incoming_queues: Dict[str, asyncio.Queue]


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
    id: str
    model: str
    chat_request: CompletionCreateParams


@dataclass
class InferenceResponse:
    request_id: str
    chunk: ChatCompletionChunk
