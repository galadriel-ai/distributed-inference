from uuid import UUID
from typing import Any
from typing import Dict

import httpx
from fastapi import HTTPException
from fastapi.responses import StreamingResponse

import settings
from distributedinference import api_logger
from distributedinference.domain.user.entities import User
from distributedinference.repository.agent_repository import AgentRepository

logger = api_logger.get()


async def execute(
    request: Any,
    agent_id: UUID,
    user: User,
    agent_repository: AgentRepository,
) -> StreamingResponse:
    """
    Proxy chat completion requests to the agent's TEE instance.

    This endpoint forwards requests to the TEE instance running the agent,
    supporting streaming responses for chat completions.

    Args:
        request: The incoming request
        agent_id: The ID of the agent
        user: The authenticated user
        agent_repository: Repository for agent operations

    Returns:
        Streaming response from the agent instance

    Raises:
        HTTPException: If the agent doesn't exist, doesn't have a running instance,
                      or if the proxy request fails
    """
    # Verify agent exists
    agent = await agent_repository.get_agent(agent_id)
    if not agent:
        raise HTTPException(
            status_code=404, detail=f"Agent with ID {agent_id} not found"
        )

    # Get the agent instance
    agent_instance = await agent_repository.get_agent_instance(agent_id)
    if not agent_instance:
        raise HTTPException(
            status_code=404,
            detail=f"Agent with ID {agent_id} doesn't have a running instance",
        )

    agent_instance_id = str(agent_instance.id)

    # Construct the target URL for chat completions
    target_url = (
        f"{settings.TEE_HOST_BASE_URL}tee/enclave/{agent_instance_id}/chat/completions"
    )

    # Get query parameters
    params = dict(request.query_params)

    # Get headers (excluding host and authorization)
    headers = dict(request.headers)
    headers.pop("host", None)
    headers.pop("authorization", None)

    # Stream the response
    return await _stream_response(target_url, params, headers)


async def _stream_response(
    target_url: str, params: Dict[str, Any], headers: Dict[str, str]
) -> StreamingResponse:
    """
    Stream a response from the target URL.

    Args:
        target_url: The URL to proxy the request to
        params: Query parameters to forward
        headers: Headers to forward

    Returns:
        A StreamingResponse object

    Raises:
        HTTPException: If the proxy request fails
    """
    client = httpx.AsyncClient(timeout=None)  # No timeout for streaming responses

    try:
        response = await client.get(
            target_url,
            params=params,
            headers=headers,
            follow_redirects=True,
        )

        async def stream_generator():
            try:
                async for chunk in response.aiter_bytes():
                    yield chunk
            finally:
                await client.aclose()

        return StreamingResponse(
            stream_generator(),
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.headers.get("content-type"),
        )
    except httpx.RequestError as exc:
        await client.aclose()
        raise HTTPException(
            status_code=502, detail=f"Error proxying request: {str(exc)}"
        )
