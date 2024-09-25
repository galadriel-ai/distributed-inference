from typing import List
from typing import Literal

from pydantic import BaseModel
from pydantic import Field

GetGraphType = Literal["network", "user", "node"]


class GetGraphResponse(BaseModel):
    timestamps: List[int] = Field(description="Timestamps for the graph")
    values: List[int] = Field(description="Values for the corresponding timestamps")
