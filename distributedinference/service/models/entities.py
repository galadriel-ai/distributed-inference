from typing import Dict
from typing import List

from pydantic import BaseModel
from pydantic import Field


class ModelPricingResponse(BaseModel):
    prompt: str = Field(description="Prompt pricing")
    completion: str = Field(description="Completion pricing")
    image: str = Field(description="Image pricing")
    request: str = Field(description="Request pricing")

    class Config:
        json_schema_extra = {
            "example": {
                "prompt": "0.0001",
                "completion": "0.0001",
                "image": "0",
                "request": "0",
            }
        }


class ModelResponse(BaseModel):
    id: str = Field(description="Model ID")
    name: str = Field(description="Model name")
    context_length: int = Field(description="Context length")
    max_completion_tokens: int = Field(description="Max completion tokens")
    pricing: ModelPricingResponse = Field(description="Model pricing")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "meta/llama3.1-70b-instruct",
                "name": "meta/llama3.1-70b-instruct",
                "context_length": 131072,
                "max_completion_tokens": 2048,
                "pricing": ModelPricingResponse.Config.json_schema_extra["example"],
            }
        }


class ModelsResponse(BaseModel):
    data: List[ModelResponse] = Field(description="List of models")

    class Config:
        json_schema_extra = {
            "example": {
                "data": [ModelResponse.Config.json_schema_extra["example"]],
            }
        }
