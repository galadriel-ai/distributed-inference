import time

from openai.types.chat import ChatCompletionMessage
from openai.types.chat.chat_completion import Choice

from distributedinference.service.completions.entities import ChatCompletion
from distributedinference.service.completions.entities import ChatCompletionRequest


async def execute(request: ChatCompletionRequest) -> ChatCompletion:
    return ChatCompletion(
        id="id",
        choices=[Choice(
            finish_reason="stop",
            index=0,
            message=ChatCompletionMessage(
                content=f"echo: {request.messages[0].content}",
                role="assistant"
            )
        )],
        created=int(time.time()),
        model=request.model,
        object="chat.completion"
    )
