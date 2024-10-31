from typing import List

from openai.types.chat import ChatCompletionMessageToolCall
from openai.types.chat.chat_completion_chunk import ChoiceDeltaToolCall
from openai.types.chat.chat_completion_chunk import ChoiceDeltaToolCallFunction
from openai.types.chat.chat_completion_message_tool_call import Function

from distributedinference.service.completions import (
    convert_tool_call_chunks_to_non_streaming as service,
)


def _get_chunks(index: int, call_id: str) -> List[ChoiceDeltaToolCall]:
    return [
        ChoiceDeltaToolCall(
            index=index,
            id=call_id,
            function=ChoiceDeltaToolCallFunction(arguments=None, name="web_search"),
            type="function",
        ),
        ChoiceDeltaToolCall(
            index=index,
            id=None,
            function=ChoiceDeltaToolCallFunction(arguments='{"query": "', name=None),
            type=None,
        ),
        ChoiceDeltaToolCall(
            index=index,
            id=None,
            function=ChoiceDeltaToolCallFunction(arguments='Hello"}', name=None),
            type=None,
        ),
        ChoiceDeltaToolCall(
            index=index,
            id=None,
            function=ChoiceDeltaToolCallFunction(arguments="", name=None),
            type=None,
        ),
    ]


def test_empty():
    response = service.execute([])
    assert response == []


def test_success():
    chunks = _get_chunks(0, "chatcmpl-tool-ad426b705e034077afa7c7d251a777b8")
    response = service.execute(chunks)
    assert response == [
        ChatCompletionMessageToolCall(
            id="chatcmpl-tool-ad426b705e034077afa7c7d251a777b8",
            type="function",
            function=Function(
                name="web_search",
                arguments='{"query": "Hello"}',
            ),
        )
    ]


def test_success_multiple_calls():
    chunks = _get_chunks(0, "chatcmpl-tool-0")
    other_chunks = _get_chunks(1, "chatcmpl-tool-1")
    other_chunks[0].function.name = "other_name"
    chunks.extend(other_chunks)
    response = service.execute(chunks)
    assert response == [
        ChatCompletionMessageToolCall(
            id="chatcmpl-tool-0",
            type="function",
            function=Function(
                name="web_search",
                arguments='{"query": "Hello"}',
            ),
        ),
        ChatCompletionMessageToolCall(
            id="chatcmpl-tool-1",
            type="function",
            function=Function(
                name="other_name",
                arguments='{"query": "Hello"}',
            ),
        ),
    ]


def test_malformed():
    chunks = [
        ChoiceDeltaToolCall(
            index=2,
            id="asd",
        ),
    ]
    response = service.execute(chunks)
    assert response == [
        ChatCompletionMessageToolCall.construct(
            None, **{"id": "asd", "function": {"name": None, "arguments": ""}}
        )
    ]
