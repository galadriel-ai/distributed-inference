from typing import AsyncGenerator
from typing import Optional
from uuid import UUID

import openai

import settings
from distributedinference.api_logger import api_logger
from distributedinference.domain.node.entities import InferenceError
from distributedinference.domain.node.entities import InferenceErrorStatusCodes
from distributedinference.domain.node.entities import InferenceRequest
from distributedinference.domain.node.entities import InferenceResponse

logger = api_logger.get()

BASE_URL = "https://api.together.xyz/v1"

MODELS_MAP = {
    "neuralmagic/Meta-Llama-3.1-8B-Instruct-FP8": "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
    "neuralmagic/Meta-Llama-3.1-70B-Instruct-quantized.w4a16": "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
    "neuralmagic/Meta-Llama-3.1-405B-Instruct-quantized.w4a16": "meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo",
}


async def execute(
    request: InferenceRequest, node_uid: UUID
) -> AsyncGenerator[Optional[InferenceResponse], None]:
    client = openai.AsyncOpenAI(base_url=BASE_URL, api_key=settings.TOGETHER_AI_API_KEY)
    # Force streaming and token usage inclusion

    model = _match_model(request.model)
    if not model:
        yield None
        return
    request.model = model
    request.chat_request["model"] = model
    request.chat_request["stream"] = True  # type: ignore
    request.chat_request["stream_options"] = {"include_usage": True}
    try:
        completion = await client.chat.completions.create(**request.chat_request)  # type: ignore
        async for chunk in completion:  # type: ignore
            yield InferenceResponse(
                node_id=node_uid,
                request_id=request.id,
                chunk=chunk,
            )
    except openai.APIStatusError as exc:
        try:
            status_code = InferenceErrorStatusCodes(exc.status_code)
        except ValueError:
            status_code = InferenceErrorStatusCodes.BAD_REQUEST
        yield InferenceResponse(
            node_id=node_uid,
            request_id=request.id,
            error=InferenceError(
                status_code=status_code,
                message=str(exc),
            ),
        )
    except Exception as exc:
        yield InferenceResponse(
            node_id=node_uid,
            request_id=request.id,
            error=InferenceError(
                status_code=InferenceErrorStatusCodes.INTERNAL_SERVER_ERROR,
                message=str(exc),
            ),
        )


def _match_model(model: str) -> Optional[str]:
    try:
        return MODELS_MAP[model]
    except Exception as exc:
        logger.error(f"Failed to match model name in llm_inference_proxy, exc: {exc}")
        return None
