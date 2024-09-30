from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class NodeStats:
    requests_served: Optional[int] = 0
    average_time_to_first_token: Optional[float] = 0.0

    benchmark_tokens_per_second: Optional[float] = 0
    benchmark_model_name: Optional[str] = None
    benchmark_created_at: Optional[datetime] = None


@dataclass
class UserAggregatedStats:
    total_requests_served: Optional[int]
    average_time_to_first_token: Optional[float]
    total_tokens_per_second: Optional[float]
