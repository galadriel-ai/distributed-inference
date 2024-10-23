from pydantic import BaseModel
from pydantic import Field


class CreateCheckoutSessionRequest(BaseModel):
    payment_amount_cents: int = Field(
        description="Payment amount in cents in US dollars"
    )


class CreateCheckoutSessionResponse(BaseModel):
    redirect_url: str = Field(
        description="Redirect url to payment provider"
    )
