import ipaddress
from typing import AsyncGenerator
from typing import Optional

import openai

import settings
from distributedinference import api_logger
from distributedinference.domain.node.entities import InferenceRequest
from distributedinference.domain.node.entities import InferenceResponse

logger = api_logger.get()


# pylint: disable=R0801
async def execute(
    api_key: str, request: InferenceRequest
) -> AsyncGenerator[InferenceResponse, None]:
    peer_node_ips = settings.PEER_NODES_LIST

    for node_ip in peer_node_ips:
        base_url = _concatenate_base_url(node_ip)
        if not base_url:
            continue
        client = openai.AsyncOpenAI(base_url=base_url, api_key=api_key)

        # Use Galadriel node id to for a place holder, and the response won't be inserted into database
        node_uid = settings.GALADRIEL_NODE_INFO_ID

        # Force streaming and token usage inclusion
        request.chat_request["stream"] = True
        request.chat_request["stream_options"] = {"include_usage": True}
        try:
            completion = await client.chat.completions.create(**request.chat_request)
            async for chunk in completion:
                yield InferenceResponse(
                    node_id=node_uid,
                    request_id=request.id,
                    chunk=chunk,
                )
            logger.debug(f"Inference completed by the peer node {node_ip}")
            return
        except Exception as e:
            logger.debug(
                f"Exception occurred by the peer node {node_ip}, continue: {e}"
            )
            continue
    yield None


def _concatenate_base_url(ip: str) -> Optional[str]:
    try:
        ipaddress.ip_address(ip)
        return f"http://{ip}/v1"
    except ValueError:
        logger.error(f"Invalid peer node IP address: {ip}")
        return None
