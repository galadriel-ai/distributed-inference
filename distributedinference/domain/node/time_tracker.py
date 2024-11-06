import time
from typing import Optional

from openai.types import CompletionUsage


class TimeTracker:

    def __init__(self):
        # All times marked as time.time()
        self.start_time: float = 0.0
        self.first_token_time: float = 0.0
        self.next_token_time: float = 0.0
        self.usage: Optional[CompletionUsage] = None

    def start(self):
        self.start_time = time.time()

    def first_token_received(self):
        if not self.first_token_time:
            self.first_token_time = time.time()

    def next_token_received(self):
        self.next_token_time = time.time()

    def track_usage(self, usage: Optional[CompletionUsage]):
        self.usage = usage

    def get_time_to_first_token(self) -> float:
        """
        Returns TTFT
        """
        return self.first_token_time - self.start_time

    def get_total_time(self) -> float:
        return self.next_token_time - self.start_time

    def get_throughput(self) -> float:
        """
        Returns tokens per second since the first token was generated
        """
        if self.usage:
            duration = self.next_token_time - self.first_token_time
            if duration:
                return self.usage.completion_tokens / duration
        return 0
