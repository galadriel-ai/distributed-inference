import asyncio
import time
from typing import Awaitable
from typing import Callable

import settings
from distributedinference import api_logger
from distributedinference.crons import api_usage_job

logger = api_logger.get()


async def start_cron_jobs():
    tasks = [
        (_run_api_usage_job, "API usage noise", 300),
    ]

    await asyncio.gather(*[_cron_runner(*t) for t in tasks])
    logger.info("Cron jobs done")


async def _cron_runner(
    job_callback: Callable[..., Awaitable[None]], job_name: str, timeout: int, *args
):
    while True:
        try:
            logger.debug(f"Started {job_name} job")
            await job_callback(*args)
            logger.debug(f"Finished {job_name} job, restarting in {timeout} seconds")
            await asyncio.sleep(timeout)
        except Exception as e:
            logger.error(f"{job_name} job failed, restarting", exc_info=True)
            await asyncio.sleep(timeout)


async def _run_api_usage_job():
    await api_usage_job.execute()


if __name__ == "__main__":
    if settings.RUN_CRON_JOBS:
        asyncio.run(start_cron_jobs())
    else:
        while True:
            time.sleep(100000)
