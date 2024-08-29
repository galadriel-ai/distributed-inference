from typing import Literal
from pydantic import BaseModel
from pydantic import Field


class ApiResponse(BaseModel):
    response: Literal["OK", "NOK"] = Field(
        description="Response status, either OK or NOK."
    )
