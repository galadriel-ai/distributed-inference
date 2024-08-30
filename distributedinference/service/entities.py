from typing import Literal
from pydantic import BaseModel
from pydantic import Field


class ApiResponse(BaseModel):
    response: Literal["OK"] = Field(description="Success response", default="OK")
