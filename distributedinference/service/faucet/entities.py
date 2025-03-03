from pydantic import BaseModel, Field


class SolanaFaucetRequestModel(BaseModel):
    """Request model for faucet request"""

    address: str = Field(
        description="Address to receive tokens",
    )


class SolanaFaucetResponseModel(BaseModel):
    """Response model for Solana faucet request"""

    success: bool = Field(
        description="Whether the faucet request was successful",
    )
    transaction_signature: str | None = Field(
        default=None,
        description="Signature of the Solana transaction",
    )
    message: str | None = Field(
        default=None,
        description="Additional information about the request",
    )
