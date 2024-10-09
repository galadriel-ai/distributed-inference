from typing import AsyncIterable

from distributedinference.service import error_responses
from distributedinference.service.completions.streaming_response import (
    StreamingResponseWithStatusCode,
)


def start_chunk(status: int):
    return {
        "headers": [(b"content-type", b"text/event-stream; charset=utf-8")],
        "status": status,
        "type": "http.response.start",
    }


def end_chunk():
    return {"body": b"", "type": "http.response.body", "more_body": False}


async def stream_chunks(
    count: int,
) -> AsyncIterable:
    for i in range(count):
        yield f"{i}"


def assert_body_chunk(response_chunk, content: str):
    assert response_chunk["body"].decode("utf-8") == content
    assert response_chunk["type"] == "http.response.body"
    assert response_chunk["more_body"] is True


async def test_success():
    responses = []

    async def send(*args, **kwargs):
        responses.append(args[0])

    success_chunks_count = 5
    stream = StreamingResponseWithStatusCode(
        stream_chunks(success_chunks_count),
        media_type="text/event-stream",
    )
    await stream.stream_response(send)

    # Start chunk, content chunks, end chunk
    assert len(responses) == 7
    assert responses[0] == start_chunk(200)

    for i in range(success_chunks_count):
        # Ignore first chunk
        assert_body_chunk(responses[i + 1], f"{i}")

    assert responses[-1] == end_chunk()


async def test_first_chunk_failure():
    responses = []

    async def send(*args, **kwargs):
        responses.append(args[0])

    async def stream_start_fail() -> AsyncIterable:
        yield "asd", 500

    stream = StreamingResponseWithStatusCode(
        stream_start_fail(),
        media_type="text/event-stream",
    )
    await stream.stream_response(send)

    assert len(responses) == 3
    assert responses[0] == start_chunk(500)
    assert_body_chunk(responses[1], "asd")
    assert responses[2] == end_chunk()


async def test_streaming_invalid_status_code():
    responses = []

    async def send(*args, **kwargs):
        responses.append(args[0])

    async def streaming_failure(count: int) -> AsyncIterable:
        for i in range(count):
            yield f"{i}"
        yield "asd", 500

    success_chunks_count = 2
    stream = StreamingResponseWithStatusCode(
        streaming_failure(success_chunks_count),
        media_type="text/event-stream",
    )
    await stream.stream_response(send)

    # Start, 2 successful chunks, error chunk, end chunk
    assert len(responses) == 5
    assert responses[0] == start_chunk(200)

    for i in range(success_chunks_count):
        # Ignore first chunk
        assert_body_chunk(responses[i + 1], f"{i}")

    assert responses[-2]["body"].decode("utf-8") == "asd"
    assert responses[-2]["type"] == "http.response.body"
    assert responses[-2]["more_body"] is True

    assert responses[-1] == end_chunk()


async def test_streaming_first_chunk_raises_error():
    responses = []

    async def send(*args, **kwargs):
        responses.append(args[0])

    async def streaming_failure() -> AsyncIterable:
        raise error_responses.ValidationError()
        yield "asd"

    success_chunks_count = 2
    stream = StreamingResponseWithStatusCode(
        streaming_failure(),
        media_type="text/event-stream",
    )
    await stream.stream_response(send)

    # Start with status code, body
    assert len(responses) == 2

    assert responses[0] == start_chunk(422)
    assert responses[1]["body"].decode("utf-8") == (
        'event: error\ndata: {"error": {"message": "'
        + error_responses.ValidationError().to_message()
        + '"}}\n\n'
    )
    assert responses[1]["type"] == "http.response.body"
    assert responses[1]["more_body"] is False


async def test_streaming_chunk_raises_error():
    responses = []

    async def send(*args, **kwargs):
        responses.append(args[0])

    async def streaming_failure() -> AsyncIterable:
        yield "asd"
        raise error_responses.ValidationError()

    stream = StreamingResponseWithStatusCode(
        streaming_failure(),
        media_type="text/event-stream",
    )
    await stream.stream_response(send)

    # Start with status code, body
    assert len(responses) == 3
    assert responses[0] == start_chunk(200)

    assert_body_chunk(responses[1], "asd")

    assert responses[2]["body"].decode("utf-8") == (
        'event: error\ndata: {"error": {"message": "'
        + error_responses.ValidationError().to_message()
        + '"}}\n\n'
    )
    assert responses[2]["type"] == "http.response.body"
    assert responses[2]["more_body"] is False


async def test_streaming_chunk_raises_unexpected_error():
    responses = []

    async def send(*args, **kwargs):
        responses.append(args[0])

    async def streaming_failure() -> AsyncIterable:
        yield "asd"
        raise Exception("very unexpected error")

    stream = StreamingResponseWithStatusCode(
        streaming_failure(),
        media_type="text/event-stream",
    )
    await stream.stream_response(send)

    # Start with status code, body
    assert len(responses) == 3
    assert responses[0] == start_chunk(200)

    assert_body_chunk(responses[1], "asd")

    assert responses[2]["body"].decode("utf-8") == (
        'event: error\ndata: {"error": {"message": "'
        + error_responses.InternalServerAPIError().to_message()
        + '"}}\n\n'
    )
    assert responses[2]["type"] == "http.response.body"
    assert responses[2]["more_body"] is False
