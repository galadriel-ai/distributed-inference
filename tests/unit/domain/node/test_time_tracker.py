from typing import List
from typing import Optional
from unittest.mock import MagicMock

from openai.types import CompletionUsage
from openai.types.chat import ChatCompletionChunk
from openai.types.chat.chat_completion_chunk import Choice
from openai.types.chat.chat_completion_chunk import ChoiceDelta

from distributedinference.domain.node import time_tracker

from distributedinference.domain.node.time_tracker import TimeTracker

CHOICES_WITH_TOKENS = [
    Choice(
        delta=ChoiceDelta(
            content="Hi",
        ),
        index=0,
    )
]


def get_chunk(
    choices: List[Choice], usage: Optional[CompletionUsage] = None
) -> ChatCompletionChunk:
    chunk = ChatCompletionChunk(
        id="mock.id",
        choices=choices,
        created=123,
        model="mock/model",
        object="chat.completion.chunk",
        usage=usage,
    )
    return chunk


def setup_function():
    time_tracker.time = MagicMock()
    time_tracker.time.time.return_value = 100.00


def test_empty():
    tracker = TimeTracker()
    assert tracker.get_throughput() == 0
    assert tracker.get_time_to_first_token() == 0
    assert tracker.get_total_time() == 0


def test_start_no_chunks():
    tracker = TimeTracker()
    tracker.start()
    assert tracker.get_throughput() == 0
    assert tracker.get_time_to_first_token() == 0
    assert tracker.get_total_time() == 0


def test_start_one_chunk():
    tracker = TimeTracker()
    tracker.start()
    time_tracker.time.time.return_value = 200.0
    tracker.chunk_received(get_chunk([]))
    assert tracker.get_throughput() == 0
    assert tracker.get_time_to_first_token() == 0.0
    assert tracker.get_total_time() == 0.0


def test_start_one_chunk_with_tokens():
    tracker = TimeTracker()
    tracker.start()
    time_tracker.time.time.return_value = 200.00
    tracker.chunk_received(get_chunk(choices=CHOICES_WITH_TOKENS))
    assert tracker.get_throughput() == 1.0
    assert tracker.get_time_to_first_token() == 100.00
    assert tracker.get_total_time() == 100.00


def test_start_one_chunk_with_usage():
    tracker = TimeTracker()
    tracker.start()
    time_tracker.time.time.return_value = 200.00
    tracker.chunk_received(
        get_chunk(
            choices=CHOICES_WITH_TOKENS,
            usage=CompletionUsage(
                completion_tokens=1000,
                prompt_tokens=1000,
                total_tokens=2000,
            ),
        )
    )
    assert tracker.get_throughput() == 1.0
    assert tracker.get_time_to_first_token() == 100.00
    assert tracker.get_total_time() == 100.00


def test_start_two_chunks_no_tokens():
    tracker = TimeTracker()
    tracker.start()
    time_tracker.time.time.return_value = 200.00
    tracker.chunk_received(get_chunk([]))
    time_tracker.time.time.return_value = 300.00
    tracker.chunk_received(get_chunk([]))
    assert tracker.get_throughput() == 0.0
    assert tracker.get_time_to_first_token() == 0.0
    assert tracker.get_total_time() == 0.0


def test_start_two_chunks_with_usage_and_tokens():
    tracker = TimeTracker()
    tracker.start()
    time_tracker.time.time.return_value = 200.00
    tracker.chunk_received(get_chunk(CHOICES_WITH_TOKENS))
    time_tracker.time.time.return_value = 300.00
    tracker.chunk_received(
        get_chunk(
            choices=CHOICES_WITH_TOKENS,
            usage=CompletionUsage(
                completion_tokens=1000,
                prompt_tokens=1000,
                total_tokens=2000,
            ),
        )
    )
    assert tracker.get_throughput() == 10.0
    assert tracker.get_time_to_first_token() == 100.00
    assert tracker.get_total_time() == 200.00


def test_start_two_chunks_second_with_tokens():
    tracker = TimeTracker()
    tracker.start()
    time_tracker.time.time.return_value = 200.00
    tracker.chunk_received(get_chunk([]))
    time_tracker.time.time.return_value = 300.00
    tracker.chunk_received(
        get_chunk(
            choices=CHOICES_WITH_TOKENS,
            usage=CompletionUsage(
                completion_tokens=1000,
                prompt_tokens=1000,
                total_tokens=2000,
            ),
        )
    )
    assert tracker.get_throughput() == 1.0
    assert tracker.get_time_to_first_token() == 200.00
    assert tracker.get_total_time() == 200.00


def test_start_three_chunks_one_without_tokens():
    tracker = TimeTracker()
    tracker.start()
    time_tracker.time.time.return_value = 200.00
    tracker.chunk_received(get_chunk(CHOICES_WITH_TOKENS))
    time_tracker.time.time.return_value = 300.00
    tracker.chunk_received(get_chunk([]))
    time_tracker.time.time.return_value = 400.00
    tracker.chunk_received(
        get_chunk(
            choices=CHOICES_WITH_TOKENS,
            usage=CompletionUsage(
                completion_tokens=1000,
                prompt_tokens=1000,
                total_tokens=2000,
            ),
        )
    )
    assert tracker.get_throughput() == 5.0
    assert tracker.get_time_to_first_token() == 100.00
    assert tracker.get_total_time() == 300.00
