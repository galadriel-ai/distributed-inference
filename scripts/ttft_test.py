"""
This scripts starts out with 2k prompt tokens and goes over the 128k prompt tokens
increasing the prompt tokens by 2k at each step. As an output it expects only 1
completion token. This is to measure the TTFT in most extreme cases.

The TimeTracker is copy pasta from the actual TimeTracker - this allows to just copy
this script to what ever machine with python to run the test without getting the whole
copy of the repo.

Usage:
python ttft_test.py \
  --base-url https://api.galadriel.com/v1 \
  --api-key gal-XshqmGxTzyzSbeL3na88x3TcxaHNnc4bjZQKmZCc1gLWvkWX \
  --model llama3.1-70b

Some helpers:

Together AI
BASE_URL = "https://api.together.xyz/v1"
API_KEY = "1945d0425839ea2aad5a8d9636bf71afab1be86b7653c328f121172755facb08"
MODEL = "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo"
python ttft_test.py \
  --base-url https://api.together.xyz/v1 \
  --api-key 1945d0425839ea2aad5a8d9636bf71afab1be86b7653c328f121172755facb08 \
  --model meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo

Galadriel
BASE_URL = "https://api.galadriel.com/v1"
MODEL = "llama3.1-70b"
API_KEY = "gal-XshqmGxTzyzSbeL3na88x3TcxaHNnc4bjZQKmZCc1gLWvkWX"

Local
BASE_URL = "http://localhost:11434/v1"
API_KEY = "none"
MODEL = "neuralmagic/Meta-Llama-3.1-8B-Instruct-FP8"
MODEL = "neuralmagic/Meta-Llama-3.1-405B-Instruct-quantized.w4a16"
"""

import argparse
import asyncio
from dataclasses import dataclass
from typing import Dict

from dataclasses_json import dataclass_json

import openai

import time
from typing import Optional

from openai.types import CompletionUsage
from openai.types.chat import ChatCompletionChunk


class TimeTracker:

    def __init__(self):
        # All times marked as time.time()
        self.start_time: float = 0.0
        self.first_token_time: float = 0.0
        self.next_token_time: float = 0.0
        self.usage: Optional[CompletionUsage] = None

    def start(self):
        self.start_time = time.time()

    def chunk_received(self, chunk: Optional[ChatCompletionChunk]):
        if _is_chunk_with_tokens(chunk):
            if self.first_token_time:
                self.next_token_time = time.time()
            else:
                self.first_token_time = time.time()

        if chunk and chunk.usage:
            self.usage = chunk.usage

    def get_time_to_first_token(self) -> float:
        """
        Returns TTFT
        """
        if self.first_token_time:
            return self.first_token_time - self.start_time
        return 0.0

    def get_total_time(self) -> float:
        if self.next_token_time:
            return self.next_token_time - self.start_time
        if self.first_token_time:
            return self.first_token_time - self.start_time
        return 0.0

    def get_throughput(self) -> float:
        """
        Returns tokens per second since the first token was generated
        """
        if self.usage and self.next_token_time:
            duration = self.next_token_time - self.first_token_time
            if duration:
                return self.usage.completion_tokens / duration
        return 0.0


def _is_chunk_with_tokens(chunk: Optional[ChatCompletionChunk]):
    return (
        chunk
        and chunk.choices
        and chunk.choices[0].delta
        and (
            chunk.choices[0].delta.content
            or chunk.choices[0].delta.function_call
            or chunk.choices[0].delta.tool_calls
        )
    )


def get_long_text():
    with open("data/long_text.txt", "r") as file:
        return file.read()


@dataclass_json
@dataclass
class InferenceRequest:
    id: str
    chat_request: Dict
    type: Optional[str] = None

    # pylint: disable=too-many-boolean-expressions, no-else-return
    @staticmethod
    def get_inference_request(parsed_data):
        if (
            parsed_data.get("id") is not None
            and parsed_data.get("chat_request") is not None
        ):
            type_field = None
            if "type" in parsed_data:
                type_field = parsed_data["type"]
            return InferenceRequest(
                id=parsed_data["id"],
                type=type_field,
                chat_request=parsed_data["chat_request"],
            )
        else:
            return None


async def llm_inference(text: str, base_url: str, api_key: str, model: str):
    client = openai.AsyncOpenAI(base_url=base_url, api_key=api_key)
    request = InferenceRequest(
        id="mock_id",
        chat_request={
            "model": model,
            "messages": [
                {"content": "You are a helpful assistant.", "role": "system"},
                {"content": text, "role": "user"},
            ],
            "max_tokens": 1,
        },
    )
    request.chat_request["stream"] = True
    request.chat_request["stream_options"] = {"include_usage": True}
    tracker = TimeTracker()
    tracker.start()
    try:
        completion = await client.chat.completions.create(**request.chat_request)
        async for chunk in completion:
            tracker.chunk_received(chunk)
    except openai.APIStatusError as exc:
        print("EXC:", exc)
    except Exception as exc:
        print("EXC:", exc)

    return tracker


def append_output(tracker: TimeTracker):
    with open("output.txt", "a") as file:
        file.write(
            f"{tracker.usage.prompt_tokens} tokens - {tracker.get_time_to_first_token()} seconds\n"
        )


async def main(base_url: str, api_key: str, model: str, concurrency: int):
    print("concurrency:", concurrency)
    tasks = []
    for i in range(concurrency):
        task = asyncio.create_task(runnable(base_url, api_key, model))
        tasks.append(task)

    results = await asyncio.gather(*tasks)
    print(f"\n\nResults: {results}")


async def runnable(base_url: str, api_key: str, model: str):
    for i in range(1, 60):
        text = get_long_text()
        n = i * 10000
        text = text[:n]
        tracker = await llm_inference(
            text=text, base_url=base_url, api_key=api_key, model=model
        )
        print("\nUsage:")
        print(tracker.usage)
        print("Tracker:")
        print("ttft:      ", tracker.get_time_to_first_token())
        print("total time:", tracker.get_total_time())
        print("throughput:", tracker.get_throughput())
        append_output(tracker)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--base-url",
        help="Base url, for example: https://api.galadriel.com/v1",
        required=True,
    )
    parser.add_argument(
        "--api-key", help="API key of the service, for example: gal-Xshqm..."
    )
    parser.add_argument("--model", help="Model name, for example: llama3.1-70b")
    parser.add_argument("--concurrency", required=False, type=int, default=1)
    args = parser.parse_args()
    asyncio.run(
        main(
            base_url=args.base_url,
            api_key=args.api_key,
            model=args.model,
            concurrency=args.concurrency,
        )
    )
