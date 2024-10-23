import stripe
from fastapi import APIRouter
from fastapi import Depends
from starlette import status
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.responses import RedirectResponse

import settings
from distributedinference import api_logger
from distributedinference import dependencies
from distributedinference.domain.user.entities import User
from distributedinference.repository.payment_api_repository import PaymentApiRepository
from distributedinference.service import error_responses
from distributedinference.service.auth import authentication
from distributedinference.service.payment import create_checkout_session_service
from distributedinference.service.payment.entities import CreateCheckoutSessionRequest

TAG = "Payment"
router = APIRouter(prefix="/payment")
router.tags = [TAG]

logger = api_logger.get()


@router.post(
    "/create-checkout-session",
    summary="Create checkout session",
    description="Creates a checkout session for users to buy credits, redirects to /payment/webhook endpoint",
    response_description="Returns a redirect response to the payment provider.",
    include_in_schema=not settings.is_production(),
)
async def signup(
    request: CreateCheckoutSessionRequest,
    # TODO: session token based auth
    # user: User = Depends(authentication.validate_session_token),
    user: User = Depends(authentication.validate_api_key_header),
    payment_api_repository: PaymentApiRepository = Depends(dependencies.get_payment_api_repository),
):
    response = await create_checkout_session_service.execute(
        request, user, payment_api_repository
    )
    # TODO: Do we want to return a redirect response here, instead of just returning the URL
    #  and having the frontend do the redirect manually?
    return RedirectResponse(
        url=response.redirect_url, status_code=status.HTTP_303_SEE_OTHER
    )


# TODO: settings
endpoint_secret = "whsec_665e002611cf0a5047023f5b7a642db919d615c727613476eb16efee07975ec8"


@router.post("/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError as e:
        raise error_responses.ValidationError()
    except stripe.error.SignatureVerificationError as e:
        raise error_responses.ValidationError()

    # charge.succeeded seems like the correct one? or payment_intent.succeeded
    if event['type'] in ["checkout.session.completed", "charge.succeeded", "payment_intent.succeeded"]:
        session = event['data']['object']
        if session["captured"]: # or ["paid"]?
            user_id = session['metadata']['user_id']
            credit_amount = int(session["amount_captured"])

        # Call your function to update the user's credit balance
        # await update_user_credits(user_id, credit_amount)

    return JSONResponse({'status': 'success'})
