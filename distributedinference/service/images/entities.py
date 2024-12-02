from typing import List, Literal, Optional
from uuid import UUID
from pydantic import BaseModel
from pydantic import Field


class ImageGenerationRequest(BaseModel):
    prompt: str = Field(description="text description of the desired image(s).")
    model: str = Field(description="The model to use for image generation.")
    n: int = Field(
        description="The number of images to generate. Must be between 1 and 10.",
        ge=1,
        le=10,
        default=1,
    )
    quality: Literal["standard", "hd"] = Field(
        description="The quality of the image that will be generated.",
        default="standard",
    )
    response_format: Literal["url", "b64_json"] = Field(
        description="The format in which the generated images are returned.",
        default="url",
    )
    size: Literal["256x256", "512x512", "1024x1024"] = Field(
        description="The size of the generated images.",
        default="1024x1024",
    )
    style: Literal["vivid", "natural"] = Field(
        description="The style of the generated images.",
        default="vivid",
    )
    user: Optional[str] = Field(
        description="A unique identifier representing your end-user", default=None
    )

    class Config:
        json_schema_extra = {
            "example": {
                "prompt": "a red apple",
                "model": "dall-e-3",
                "n": 1,
                "quality": "standard",
                "response_format": "url",
                "size": "1024x1024",
                "style": "vivid",
                "user": "user123",
            }
        }


class ImageEditRequest(BaseModel):
    image: str = Field(description="The image to edit.")
    prompt: str = Field(description="A text description of the desired image(s).")
    mask: Optional[str] = Field(
        description="The mask to apply to the image.",
        default=None,
    )
    model: str = Field(description="The model to use for image editing.")
    n: int = Field(
        description="The number of images to generate. Must be between 1 and 10.",
        ge=1,
        le=10,
        default=1,
    )
    response_format: Literal["url", "b64_json"] = Field(
        description="The format in which the generated images are returned.",
        default="url",
    )
    size: Literal["256x256", "512x512", "1024x1024"] = Field(
        description="The size of the generated images.",
        default="1024x1024",
    )
    user: Optional[str] = Field(
        description="A unique identifier representing your end-user", default=None
    )

    class Config:
        json_schema_extra = {
            "example": {
                "image": "https://example.com/image.png",
                "prompt": "a red apple",
                "mask": None,
                "model": "dall-e-3",
                "n": 1,
                "response_format": "url",
                "size": "1024x1024",
                "user": "user123",
            }
        }
