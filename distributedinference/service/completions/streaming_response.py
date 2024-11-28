import json
from typing import AsyncIterator

from fastapi.responses import StreamingResponse
from starlette.types import Send

from distributedinference import api_logger
from distributedinference.service import error_responses

logger = api_logger.get()


class StreamingResponseWithStatusCode(StreamingResponse):
    """
    Variation of StreamingResponse that can dynamically decide the HTTP status code,
    based on the return value of the content iterator (parameter `content`).
    Expects the content to yield either just str content as per the original `StreamingResponse`
    or else tuples of (`content`: `str`, `status_code`: `int`).
    """

    body_iterator: AsyncIterator[str | bytes]
    response_started: bool = False

    async def stream_response(self, send: Send) -> None:
        more_body = True
        try:
            # pylint: disable=C2801
            first_chunk = await self.body_iterator.__anext__()
            if isinstance(first_chunk, tuple):
                first_chunk_content, self.status_code = first_chunk
            else:
                first_chunk_content = first_chunk
            if isinstance(first_chunk_content, str):
                first_chunk_content = first_chunk_content.encode(self.charset)

            await send(
                {
                    "type": "http.response.start",
                    "status": self.status_code,
                    "headers": self.raw_headers,
                }
            )
            self.response_started = True
            await send(
                {
                    "type": "http.response.body",
                    "body": first_chunk_content,
                    "more_body": more_body,
                }
            )

            async for chunk in self.body_iterator:
                if isinstance(chunk, tuple):
                    content, status_code = chunk
                    if 200 <= status_code <= 299:
                        # An error occurred mid-stream
                        if not isinstance(content, bytes):
                            content = content.encode(self.charset)
                        more_body = False
                        await send(
                            {
                                "type": "http.response.body",
                                "body": content,
                                "more_body": more_body,
                            }
                        )
                        return
                else:
                    content = chunk

                if isinstance(content, str):
                    content = content.encode(self.charset)
                more_body = True
                await send(
                    {
                        "type": "http.response.body",
                        "body": content,
                        "more_body": more_body,
                    }
                )

        except error_responses.APIErrorResponse as exc:
            logger.error("APIErrorResponse streaming_error", exc_info=True)
            more_body = False
            await self._send_error(exc, send)
        except Exception:
            error = error_responses.InternalServerAPIError()
            logger.error("unhandled_streaming_error", exc_info=True)
            more_body = False
            await self._send_error(error, send)
        if more_body:
            await send({"type": "http.response.body", "body": b"", "more_body": False})

    async def _send_error(
        self, exc: error_responses.APIErrorResponse, send: Send
    ) -> None:
        error_resp = {"error": {"message": exc.to_message()}}
        error_event = f"event: error\ndata: {json.dumps(error_resp)}\n\n".encode(
            self.charset
        )
        if not self.response_started:
            await send(
                {
                    "type": "http.response.start",
                    "status": exc.to_status_code(),
                    "headers": self.raw_headers,
                }
            )
        await send(
            {
                "type": "http.response.body",
                "body": error_event,
                "more_body": False,
            }
        )
