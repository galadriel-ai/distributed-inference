import asyncio
from typing import Awaitable
from typing import Callable

import settings
from distributedinference import api_logger
from distributedinference import dependencies
from distributedinference.crons.attestation import agent_attestations_job
from distributedinference.crons import api_usage_job
from distributedinference.crons import billing_job
from distributedinference.crons import credits_notification_job
from distributedinference.repository import connection

logger = api_logger.get()


async def start_cron_jobs():
    connection.init_defaults()
    dependencies.init_globals()

    tasks = [
        # (_run_api_usage_job, "API usage noise", 300),
    ]
    if settings.RUN_CRON_JOBS:
        tasks.append((_run_billing_job, "User billing job", 100))
        if settings.SLACK_CHANNEL_ID and settings.SLACK_OAUTH_TOKEN:
            tasks.append(
                (_run_credits_notification_job, "Credits notification job", 3600 * 6)
            )
        else:
            logger.info(
                "Not running slack credits notification job because of missing env values"
            )
        tasks.append((_run_attestations_job, "Agent attestations job", 300))

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
        except Exception:
            logger.error(f"{job_name} job failed, restarting", exc_info=True)
            await asyncio.sleep(timeout)


async def _run_api_usage_job():
    await api_usage_job.execute()


async def _run_billing_job():
    billing_repository = dependencies.get_billing_repository()
    tokens_repository = dependencies.get_tokens_repository()
    await billing_job.execute(billing_repository, tokens_repository)


async def _run_credits_notification_job():
    billing_repository = dependencies.get_billing_repository()
    await credits_notification_job.execute(billing_repository)


async def _run_attestations_job():
    agent_repository = dependencies.get_agent_repository()
    tee_repository = dependencies.get_tee_orchestration_repository()
    await agent_attestations_job.execute(agent_repository, tee_repository)


if __name__ == "__main__":
    asyncio.run(start_cron_jobs())
