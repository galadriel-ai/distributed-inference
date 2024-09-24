from typing import List

from pydantic import BaseModel
from pydantic import Field


class GetGraphResponse(BaseModel):
    timestamps: List[int] = Field(description="Timestamps for the graph")
    values: List[int] = Field(description="Values for the corresponding timestamps")
