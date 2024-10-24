from typing import AsyncGenerator
from typing import Optional
from uuid import UUID

import openai

from distributedinference import api_logger
from distributedinference.domain.node.entities import InferenceRequest
from distributedinference.domain.node.entities import InferenceResponse
from distributedinference.domain.node.entities import InferenceStatusCodes
from distributedinference.service.error_responses import InferenceError

logger = api_logger.get()

BASE_URL = "https://api.together.xyz/v1"
API_KEY = "1945d0425839ea2aad5a8d9636bf71afab1be86b7653c328f121172755facb08"
MODELS_MAP = {
    "neuralmagic/Meta-Llama-3.1-8B-Instruct-FP8": "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
    "neuralmagic/Meta-Llama-3.1-70B-Instruct-quantized.w4a16": "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
    "neuralmagic/Meta-Llama-3.1-405B-Instruct-quantized.w4a16": "meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo",
}


async def execute(
    request: InferenceRequest, node_uid: UUID
) -> AsyncGenerator[InferenceResponse, None]:
    client = openai.AsyncOpenAI(base_url=BASE_URL, api_key=API_KEY)
    # Force streaming and token usage inclusion

    model = _match_model(request.model)
    if not model:
        return
    request.model = model
    request.chat_request["model"] = model

    request.chat_request["stream"] = True
    request.chat_request["stream_options"] = {"include_usage": True}
    try:
        completion = await client.chat.completions.create(**request.chat_request)
        async for chunk in completion:
            print("\nCHUNK:", chunk)
            yield InferenceResponse(
                node_id=node_uid,
                request_id=request.id,
                chunk=chunk,
            )
    except openai.APIStatusError as exc:
        print("EXCEPTION:", exc)
        yield InferenceResponse(
            node_id=node_uid,
            request_id=request.id,
            error=InferenceError(
                node_id=node_uid,
                status_code=InferenceStatusCodes(exc.status_code),
                message_extra=str(exc),
            ),
        )
    except Exception as exc:
        yield InferenceResponse(
            node_id=node_uid,
            request_id=request.id,
            error=InferenceError(
                node_id=node_uid,
                status_code=InferenceStatusCodes.INTERNAL_SERVER_ERROR,
                message_extra=str(exc),
            ),
        )


def _match_model(model: str) -> Optional[str]:
    try:
        return MODELS_MAP[model]
    except Exception as exc:
        logger.error(f"Failed to match model name in llm_inference_proxy, exc: {exc}")
        return None
