from pydantic import BaseModel, Field


class SolanaFaucetRequest(BaseModel):
    """Request model for Solana faucet request"""

    address: str = Field(
        ...,
        description="Solana address to receive SOL",
        example="HdMTSNxh9iUnVjM6tJ14WBcEuzWenSBXMXPFkD87wRmf",
    )


class SolanaFaucetResponseModel(BaseModel):
    """Response model for Solana faucet request"""

    success: bool = Field(
        ...,
        description="Whether the faucet request was successful",
        example=True,
    )
    transaction_signature: str = Field(
        None,
        description="Signature of the Solana transaction",
        example="5UfDMnxy9FkZfSCBCXHBrrJusqSEpZUkZFuTZQV3Aif5GJVyUxvd1VgcCzTbry1FkZ5B679Jwb6wJmPcPXQRZqQT",
    )
    message: str = Field(
        None,
        description="Additional information about the request",
        example="Successfully sent 0.0001 SOL",
    )
