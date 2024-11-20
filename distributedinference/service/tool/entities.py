from typing import Dict
from typing import List

from pydantic import BaseModel
from pydantic import Field


class SearchRequest(BaseModel):
    query: str = Field(description="Search query")
    max_results: int = Field(
        description="Search query",
        ge=1,
        le=10,
        default=5,
    )


class SearchResponse(BaseModel):
    results: List[Dict] = Field(description="Search results")
