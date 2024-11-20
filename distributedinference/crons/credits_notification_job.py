from decimal import Decimal
from typing import List
from typing import Optional

import aiohttp

import settings
from distributedinference import api_logger
from distributedinference.domain.billing.entities import CreditsReport
from distributedinference.repository.billing_repository import BillingRepository

logger = api_logger.get()


async def execute(billing_repository: BillingRepository) -> None:
    reports = await _get_reports(billing_repository)

    formatted_message = (
        "| Percentage left | credits | last credits addition | Email |\n\n"
    )
    for report in reports:
        formatted_message += f"| {_format_percentage(report.percentage_left)} | {_format_credits(report.credits)} | {_format_credits(report.latest_credits_addition)} | {report.email} |\n"

    await _send_slack_message(formatted_message)


async def _get_reports(billing_repository: BillingRepository) -> List[CreditsReport]:
    reports = await billing_repository.get_credits_reports()
    for report in reports:
        if report.latest_credits_addition and report.latest_credits_addition >= 0:
            report.percentage_left = (
                report.credits / report.latest_credits_addition
            ) * Decimal("100")
        else:
            report.percentage_left = Decimal("0")
    reports = sorted(reports, key=lambda x: x.percentage_left or Decimal("0"))
    return reports


def _format_credits(credits_amount: Decimal):
    try:
        return f"${round(credits_amount, 2)}"
    except Exception:
        return f"${credits_amount}"


def _format_percentage(percentage: Optional[Decimal]) -> str:
    if not percentage:
        return "🔴 -"
    if percentage < 10:
        return f"🔴 {round(percentage, 2)}%"
    if percentage < 25:
        return f"🟠 {round(percentage, 2)}%"
    if percentage < 50:
        return f"🟡 {round(percentage, 2)}%"
    return f"🟢 {round(percentage, 2)}%"


async def _send_slack_message(formatted_message: str):
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        response = await session.post(
            "https://slack.com/api/chat.postMessage",
            headers={"Authorization": f"Bearer {settings.SLACK_OAUTH_TOKEN}"},
            data={"channel": settings.SLACK_CHANNEL_ID, "text": formatted_message},
        )
        response_json = await response.json()
        if response_json.get("error"):
            logger.error(
                f"credits_notification_job failed: {response_json.get('error')}"
            )
