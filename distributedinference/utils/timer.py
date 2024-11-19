"""
Timer decorator to profile the durations of function executions.

Usage:
```python
from distributedinference.utils.timer import async_timer

logger = api_logger.get()

@async_timer("my_file.do_stuff", logger=logger)
async def do_stuff():
    await asyncio.sleep(1)
```

In the logs you will see:
{
  "asctime": "2024-10-17 11:34:18,471",
  "name": "DISTRIBUTED_INFERENCE",
  "levelname": "INFO",
  "message": "Timer: my_file.do_stuff took 1.001923 s",
  "taskName": "Task-1"
}

"""

import logging
from datetime import datetime
from datetime import timezone
from typing import Optional


class Timer:
    """Measure elapsed time"""

    started_at: datetime
    ended_at: Optional[datetime] = None
    message_at: Optional[datetime] = None

    def __init__(self, text=None, iterable=None, logger=None, interval=None):
        self.text = text
        self.iterable = iterable
        self.interval = interval
        self.logger = logging.getLogger(__name__) if logger is None else logger

    @property
    def elapsed(self) -> float:
        """Elapsed time in seconds"""
        if self.ended_at is None:
            return (datetime.now(timezone.utc) - self.started_at).total_seconds()
        return (self.ended_at - self.started_at).total_seconds()

    def _refresh(self, i):
        if self.interval is None:
            return
        now = datetime.now(timezone.utc)
        if (
            self.message_at is None
            or (now - self.message_at).total_seconds() > self.interval
        ):
            self.message_at = now
            self.logger.info("%s progress %d/%d", self.text, i, len(self))

    def __len__(self) -> int:
        return len(self.iterable)

    def __iter__(self):
        for i, item in enumerate(self.iterable):
            self._refresh(i)
            yield item

    async def __aenter__(self):
        self.started_at = datetime.now(timezone.utc)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.ended_at = datetime.now(timezone.utc)
        if self.text is not None:
            self.logger.info("Timer: %s took %f s", self.text, self.elapsed)


def async_timer(name: str, logger: logging.Logger):
    def decorator(function):
        async def wrapper(*args, **kwargs):
            async with Timer(name, logger=logger):
                return await function(*args, **kwargs)

        return wrapper

    return decorator
