from typing import Optional
from uuid import UUID

import stripe

from distributedinference.domain.payment.entities import PaymentAmount


class PaymentApiRepository:

    def __init__(self, api_key: Optional[str]):
        if api_key:
            stripe.api_key = api_key

    async def create_checkout_session(self, user_id: UUID, payment_amount: PaymentAmount):
        # Stripe calls /webhook endpoint on backend on success/fail
        session = await stripe.checkout.Session.create_async(
            payment_method_types=["card"],
            client_reference_id=str(user_id),
            line_items=[{
                "price_data": {
                    "currency": payment_amount.currency,
                    "product_data": {
                        "name": f"Purchase {payment_amount.cents} credits",
                    },
                    "unit_amount": payment_amount.cents,
                },
                "quantity": 1,
            }],
            mode="payment",
            # TODO: frontend success url!
            success_url="http://localhost:3000/success",
            cancel_url="http://localhost:3000/cancel",
            # metadata={"user_id": user_id, "credit_amount": payment_amount.cents}
        )
        return session.url
