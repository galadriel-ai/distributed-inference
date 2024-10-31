from collections import defaultdict
from typing import List

from openai.types.chat import ChatCompletionMessageToolCall
from openai.types.chat.chat_completion_chunk import ChoiceDeltaToolCall


def execute(
    tool_chunks: List[ChoiceDeltaToolCall],
) -> List[ChatCompletionMessageToolCall]:
    """
    Converts tool_chunks gotten from streaming LLM response (chunk.choices[0].delta.tool_calls)
    to a response that can be used in a non-streaming
    response ["choices"][n]["message"]["tool_calls"]

    :param tool_chunks: tool_calls gotten from LLM stream chunks
    :return: Non-streaming tool call response
    """
    tool_calls_dict = defaultdict(
        lambda: {"id": None, "function": {"arguments": "", "name": None}, "type": None}
    )

    for tool_call in tool_chunks:
        if tool_call.id is not None:
            tool_calls_dict[str(tool_call.index)]["id"] = tool_call.id
        if tool_call.function.name is not None:
            tool_calls_dict[str(tool_call.index)]["function"][
                "name"
            ] = tool_call.function.name
        if tool_call.function.arguments:
            # Arguments are chunked, everything else, if present, is contained in a single chunk
            tool_calls_dict[str(tool_call.index)]["function"][
                "arguments"
            ] += tool_call.function.arguments
        if tool_call.type is not None:
            tool_calls_dict[str(tool_call.index)]["type"] = tool_call.type

    tool_calls_list = list(tool_calls_dict.values())
    return [ChatCompletionMessageToolCall.construct(None, **t) for t in tool_calls_list]
