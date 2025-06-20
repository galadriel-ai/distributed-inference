from typing import Dict
from typing import List
from typing import Literal
from typing import Optional
from typing import Union
from typing import cast

from openai._utils import async_maybe_transform
from openai.types.chat import ChatCompletion as OpenAiChatCompletion
from openai.types.chat import CompletionCreateParams
from openai.types.chat import completion_create_params
from pydantic import BaseModel
from pydantic import Field

from distributedinference import api_logger

logger = api_logger.get()


class FunctionCall(BaseModel):
    arguments: str = Field(
        description="The name and arguments of a function that should be called, as generated by the model."
    )
    name: str = Field(description="The name of the function to call.")


class BaseMessage(BaseModel):
    content: Optional[str] = Field(
        description="The contents of the message. `content` is required for all messages, and may be null for assistant messages with function calls."
    )
    function_call: Optional[FunctionCall] = Field(
        description="The name and arguments of a function that should be called, as generated by the model.",
        default=None,
    )
    role: str = Field(description="One of: `system`, `assistant`, `user` or `tool`")


class Message(BaseMessage):
    name: Optional[str] = Field(
        description="The name of the author of this message. `name` is required if `role` is `function`, and it should be the name of the function whose response is in the content. May contain a-z, A-Z, 0-9, and underscores, with a maximum length of 64 characters.",
        default=None,
    )


class JsonSchema(BaseModel):
    description: Optional[str] = Field(
        description="A description of what the response format is for, used by the model to determine how to respond in the format.",
        default=None,
    )
    name: str = Field(
        description="The name of the response format. Must be a-z, A-Z, 0-9, or contain underscores and dashes, with a maximum length of 64.",
    )
    schema: Optional[Dict] = Field(
        description="The schema for the response format, described as a JSON Schema object.",
    )  # type: ignore
    strict: Optional[bool] = Field(
        description="Whether to enable strict schema adherence when generating the output. If set to true, the model will always follow the exact schema defined in the schema field. Only a subset of JSON Schema is supported when `strict` is `true`.",
        default=None,
    )


class ResponseFormat(BaseModel):
    type: Literal["text", "json_object", "json_schema"] = Field(
        description="The type of response format being defined: `text`",
    )
    json_schema: Optional[JsonSchema] = Field(default=None)


class StreamOptions(BaseModel):
    include_usage: bool = Field(
        description="If set, an additional chunk will be streamed before the `data: [DONE]` message. The usage field on this chunk shows the token usage statistics for the entire request, and the choices field will always be an empty array. All other chunks will also include a usage field, but with a null value.",
    )


class Function(BaseModel):
    description: Optional[str] = Field(
        description="A description of what the function does, used by the model to choose when and how to call the function.",
        default=None,
    )
    name: str = Field(
        description="The name of the function to be called. Must be a-z, A-Z, 0-9, or contain underscores and dashes, with a maximum length of 64.",
    )
    parameters: Dict = Field(
        description='The parameters the functions accepts, described as a JSON Schema object. See the guide for examples, and the JSON Schema reference for documentation about the format. To describe a function that accepts no parameters, provide the value {"type": "object", "properties": {}}.'
    )
    strict: Optional[bool] = Field(
        description="Whether to enable strict schema adherence when generating the function call. If set to true, the model will follow the exact schema defined in the parameters field. Only a subset of JSON Schema is supported when `strict` is `true`.",
        default=False,
    )


class Tool(BaseModel):
    type: Optional[Literal["function"]] = Field(
        description="The type of the tool. Currently, only `function` is supported."
    )
    function: Function = Field()


class ToolChoiceFunction(BaseModel):
    name: str = Field(description="The name of the function to call.")


class ToolChoice(BaseModel):
    type: Optional[Literal["function"]] = Field(
        description="The type of the tool. Currently, only `function` is supported.",
    )
    function: ToolChoiceFunction = Field()


class ChatCompletionRequest(BaseModel):
    messages: List[Message] = Field(
        ..., description="A list of messages comprising the conversation so far. "
    )
    model: str = Field(
        description="ID of the model to use. Get ID for available [models](/for-developers/models)."
    )
    frequency_penalty: Optional[float] = Field(
        description="Number between -2.0 and 2.0. Positive values penalize new tokens based on their existing frequency in the text so far, decreasing the model's likelihood to repeat the same line verbatim.",
        default=None,
    )
    logit_bias: Optional[Dict] = Field(
        description="Modify the likelihood of specified tokens appearing in the completion.",
        default=None,
    )
    logprobs: Optional[bool] = Field(
        description="Whether to return log probabilities of the output tokens or not. If true, returns the log probabilities of each output token returned in the `content` of `message`.",
        default=False,
    )
    top_logprobs: Optional[int] = Field(
        description="An integer between 0 and 20 specifying the number of most likely tokens to return at each token position, each with an associated log probability. `logprobs` must be set to `true` if this parameter is used.",
        default=None,
    )
    max_tokens: Optional[int] = Field(
        description="The maximum number of tokens to generate in the chat completion. [Models](/for-developers/models) specific.",
        default=None,
    )
    n: Optional[int] = Field(
        description="How many chat completion choices to generate for each input message.",
        default=None,
    )
    presence_penalty: Union[float, List, None] = Field(
        description="Number between -2.0 and 2.0. Positive values penalize new tokens based on whether they appear in the text so far, increasing the model's likelihood to talk about new topics.",
        default=0,
    )
    response_format: Optional[ResponseFormat] = Field(
        description="An object specifying the format that the model must output.",
        default=None,
    )
    seed: Optional[int] = Field(
        description="This feature is in Beta. If specified, our system will make a best effort to sample deterministically, such that repeated requests with the same `seed` and parameters should return the same result. Determinism is not guaranteed, and you should refer to the `system_fingerprint` response parameter to monitor changes in the backend.",
        default=None,
    )
    # service_tier: Optional[str] = Field(
    #     description="",
    #     default=None,
    # )
    stop: Union[str, List, None] = Field(
        description="Up to 4 sequences where the API will stop generating further tokens.",
        default=None,
    )
    stream: Optional[bool] = Field(
        description="If set, partial message deltas will be sent, like in ChatGPT.",
        default=False,
    )
    stream_options: Optional[StreamOptions] = Field(
        description="Options for streaming response. Only set this when you set `stream: true`.",
        default=None,
    )
    temperature: Optional[float] = Field(
        description="What sampling temperature to use, between 0 and 2. Higher values like 0.8 will make the output more random, while lower values like 0.2 will make it more focused and deterministic.",
        default=1,
    )
    top_p: Optional[float] = Field(
        description="An alternative to sampling with temperature, called nucleus sampling, where the model considers the results of the tokens with top_p probability mass. So 0.1 means only the tokens comprising the top 10% probability mass are considered.",
        default=1,
    )
    tools: Optional[List[Tool]] = Field(
        description="**Currently the 8b model does not support tools.** A list of tools the model may call. Currently, only functions are supported as a tool. Use this to provide a list of functions the model may generate JSON inputs for.",
        default=None,
    )
    tool_choice: Union[str, None, ToolChoice] = Field(
        description='Controls which (if any) tool is called by the model. none means the model will not call any tool and instead generates a message. auto means the model can pick between generating a message or calling one or more tools. required means the model must call one or more tools. Specifying a particular tool via `{"type": "function", "function": {"name": "my_function"}}` forces the model to call that tool.',
        default=None,
    )
    # parallel_tool_calls: Optional[bool] = Field(
    #     description="Whether to enable parallel function calling during tool use.",
    #     default=None,
    # )
    user: Optional[str] = Field(
        description="A unique identifier representing your end-user, which can help OpenAI to monitor and detect abuse.",
        default=None,
    )

    # function_call: Union[str, Dict, None] = Field(
    #     description='Controls how the model calls functions. "none" means the model will not call a function and instead generates a message. "auto" means the model can pick between generating a message or calling a function. Specifying a particular function via {"name": "my_function"} forces the model to call that function. "none" is the default when no functions are present. "auto" is the default if functions are present.',
    #     default=None,
    #     deprecated=True,
    # )
    # functions: Optional[List[Function]] = Field(
    #     description="A list of functions the model may generate JSON inputs for.",
    #     default=None,
    #     deprecated=True,
    # )

    class Config:
        json_schema_extra = {
            "example": {
                "model": "llama3.1",
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Hello!"},
                ],
            }
        }

    async def to_openai_chat_completion(self) -> CompletionCreateParams:
        try:
            dict_input = {
                "messages": self.messages,
                "model": self.model,
                "frequency_penalty": self.frequency_penalty,
                # "function_call": self.function_call,
                # "functions": self.functions,
                "logit_bias": self.logit_bias,
                "logprobs": self.logprobs,
                "max_tokens": self.max_tokens,
                # lmdeploy doesn't like this param
                # "n": self.n,
                # "parallel_tool_calls": self.parallel_tool_calls,
                "presence_penalty": self.presence_penalty,
                "response_format": self.response_format,
                "seed": self.seed,
                # "service_tier": self.service_tier,
                "stop": self.stop,
                "stream": self.stream,
                "stream_options": self.stream_options,
                "temperature": self.temperature,
                "top_logprobs": self.top_logprobs,
                "top_p": self.top_p,
                "user": self.user,
            }
            # vllm (at least <=0.6.3.post1) does not support the "tool_choice" field
            # even if the dict has it as "None" then vllm will return an error
            if self.tool_choice:
                dict_input["tool_choice"] = self.tool_choice  # type: ignore
            if self.tools:
                dict_input["tools"] = self.tools
            result = await async_maybe_transform(
                dict_input,
                completion_create_params.CompletionCreateParams,
            )
            return cast(completion_create_params.CompletionCreateParams, result)
        except Exception as e:
            logger.warning("Failed to convert input to openAI CompletionCreateParams")
            raise e


class ChatCompletion(OpenAiChatCompletion):
    pass
