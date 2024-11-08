from unittest.mock import MagicMock

from openai.types import CompletionUsage

from distributedinference.domain.node import time_tracker

from distributedinference.domain.node.time_tracker import TimeTracker


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
    time_tracker.time.time.return_value = 200.00
    tracker.chunk_received()
    assert tracker.get_throughput() == 0
    assert tracker.get_time_to_first_token() == 100.00
    assert tracker.get_total_time() == 100.00


def test_start_one_chunk_with_usage():
    tracker = TimeTracker()
    tracker.start()
    time_tracker.time.time.return_value = 200.00
    tracker.chunk_received()
    tracker.track_usage(
        CompletionUsage(
            completion_tokens=1000,
            prompt_tokens=1000,
            total_tokens=2000,
        )
    )
    assert tracker.get_throughput() == 0
    assert tracker.get_time_to_first_token() == 100.00
    assert tracker.get_total_time() == 100.00


def test_start_two_chunks():
    tracker = TimeTracker()
    tracker.start()
    time_tracker.time.time.return_value = 200.00
    tracker.chunk_received()
    time_tracker.time.time.return_value = 300.00
    tracker.chunk_received()
    assert tracker.get_throughput() == 0
    assert tracker.get_time_to_first_token() == 100.00
    assert tracker.get_total_time() == 200.00


def test_start_two_chunks_with_usage():
    tracker = TimeTracker()
    tracker.start()
    time_tracker.time.time.return_value = 200.00
    tracker.chunk_received()
    time_tracker.time.time.return_value = 300.00
    tracker.chunk_received()
    tracker.track_usage(
        CompletionUsage(
            completion_tokens=1000,
            prompt_tokens=1000,
            total_tokens=2000,
        )
    )
    assert tracker.get_throughput() == 10.0
    assert tracker.get_time_to_first_token() == 100.00
    assert tracker.get_total_time() == 200.00
