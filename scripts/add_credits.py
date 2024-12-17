import argparse
import asyncio
from typing import Optional
from uuid import UUID
from decimal import Decimal

import settings
from distributedinference.repository import connection
from distributedinference.repository.billing_repository import BillingRepository
from distributedinference.repository.user_repository import UserRepository


async def main(
    email: Optional[str],
    input_user_id: Optional[str],
    credits_amount: str,
) -> None:
    formatted_credits = Decimal(credits_amount)

    user_repository = UserRepository(
        connection.db_connection(), connection.db_connection_read()
    )
    user_id = None
    if input_user_id:
        user_id = UUID(input_user_id)
    if email:
        user = await user_repository.get_user_by_email(email.strip())
        if not user:
            print("User not found by email")
            return
        user_id = user.uid

    repo = BillingRepository(
        connection.db_connection(), connection.db_connection_read()
    )

    user_credits_before = await repo.get_user_credit_balance(user_id)
    print(f"User credits before {user_credits_before}")
    await repo.add_credits(user_id, credits, "usd")
    await repo.update_user_usage_tier(user_id, settings.PAID_USAGE_TIER_UUID)
    user_credits_after = await repo.get_user_credit_balance(user_id)
    print(f"User credits after {user_credits_after}")


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", help="User email", required=False)
    parser.add_argument(
        "--user_id", help="User id (either user_id or email required)", required=False
    )
    parser.add_argument(
        "--credits", help='Amount of credits to add as a string eg "1.2"', required=True
    )
    args = parser.parse_args()
    if not args.email and not args.user_id:
        print("Either --email or --user-id is required")
        return None, None, None
    return args.email, args.user_id, args.credits


if __name__ == "__main__":
    email, user_id, credits = parse_arguments()
    if (email or user_id) and credits:
        asyncio.run(main(email, user_id, credits))
