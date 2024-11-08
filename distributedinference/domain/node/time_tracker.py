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

    def chunk_received(self):
        if self.first_token_time:
            self.next_token_time = time.time()
        else:
            self.first_token_time = time.time()

    def track_usage(self, usage: Optional[CompletionUsage]):
        self.usage = usage

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
