from distributedinference.domain.payment.entities import PaymentAmount
from distributedinference.domain.user.entities import User
from distributedinference.repository.payment_api_repository import PaymentApiRepository
from distributedinference.service.payment.entities import CreateCheckoutSessionRequest
from distributedinference.service.payment.entities import CreateCheckoutSessionResponse


async def execute(
    request: CreateCheckoutSessionRequest,
    user: User,
    payment_api_repository: PaymentApiRepository,
) -> CreateCheckoutSessionResponse:
    session_url = await payment_api_repository.create_checkout_session(
        user.uid,
        PaymentAmount(
            cents=request.payment_amount_cents,
        )
    )
    return CreateCheckoutSessionResponse(redirect_url=session_url)
