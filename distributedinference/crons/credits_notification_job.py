import asyncio
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from decimal import Decimal
from typing import List

from slack_sdk.web.async_client import AsyncWebClient

import settings
from distributedinference import api_logger
from distributedinference.domain.billing.entities import CreditsReport
from distributedinference.repository.billing_repository import BillingRepository

# in UTC timezone!
NOTIFICATION_TIME_HOUR = 5
NOTIFICATION_TIME_MINUTE = 0

logger = api_logger.get()


async def execute(billing_repository: BillingRepository) -> None:
    # await _sleep()

    reports = await _get_reports(billing_repository)

    formatted_message = (
        "| Percentage left | credits | last credits addition | Email |\n\n"
    )
    for report in reports:
        formatted_message += f"| {_format_percentage(report.percentage_left)} | {_format_credits(report.credits)} | {_format_credits(report.latest_credits_addition)} | {report.email} |\n"

    client = AsyncWebClient(token=settings.SLACK_OAUTH_TOKEN)
    await client.chat_postMessage(
        channel=settings.SLACK_CHANNEL_ID,
        text=formatted_message,
    )


async def _sleep():
    now = datetime.now(UTC)
    target_time = now.replace(
        hour=NOTIFICATION_TIME_HOUR, minute=NOTIFICATION_TIME_MINUTE
    )
    if target_time <= now:
        target_time += timedelta(days=1)
    seconds_until_target = (target_time - now).total_seconds()
    logger.debug(
        f"credits_notification_job sleeping for {seconds_until_target} seconds"
    )
    await asyncio.sleep(seconds_until_target)


async def _get_reports(billing_repository: BillingRepository) -> List[CreditsReport]:
    reports = await billing_repository.get_credits_reports()
    for report in reports:
        if report.latest_credits_addition and report.latest_credits_addition >= 0:
            report.percentage_left = (
                report.credits / report.latest_credits_addition
            ) * Decimal("100")
        else:
            report.percentage_left = Decimal("0")
    reports = sorted(reports, key=lambda x: x.percentage_left)
    return reports


def _format_credits(credits_amount: Decimal):
    try:
        return f"${round(credits_amount, 2)}"
    except Exception:
        return f"${credits_amount}"


def _format_percentage(percentage: Decimal) -> str:
    if percentage < 10:
        return f"🔴 {round(percentage, 2)}%"
    if percentage < 25:
        return f"🟠 {round(percentage, 2)}%"
    if percentage < 50:
        return f"🟡 {round(percentage, 2)}%"
    return f"🟢 {round(percentage, 2)}%"
