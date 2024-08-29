import asyncio
from enum import Enum
from dataclasses import dataclass
from typing import Dict
from typing import List
from typing import Optional
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

    def active_requests_count(self) -> int:
        return len(self.request_incoming_queues)


class InferenceStatusCodes(Enum):
    BAD_REQUEST = 400
    AUTHENTICATION_ERROR = 401
    PERMISSION_DENIED = 403
    NOT_FOUND = 404
    CONFLICT = 409
    UNPROCESSABLE_ENTITY = 422
    RATE_LIMIT = 429
    UNKNOWN_ERROR = 500


@dataclass
class InferenceError:
    status_code: InferenceStatusCodes
    message: str


@dataclass
class InferenceRequest:
    id: str
    model: str
    chat_request: CompletionCreateParams


@dataclass
class InferenceResponse:
    request_id: str
    chunk: Optional[ChatCompletionChunk] = None
    error: Optional[InferenceError] = None
