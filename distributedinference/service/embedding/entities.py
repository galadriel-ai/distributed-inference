from typing import List
from typing import Literal
from typing import Optional
from typing import Union

from pydantic import BaseModel
from pydantic import Field


class EmbeddingRequest(BaseModel):
    input: Union[str, List[str], List[int], List[List[int]]] = Field(
        description="Input text to embed, encoded as a string or array of tokens. "
        "To embed multiple inputs in a single request, pass an array of strings "
        "or array of token arrays. The input must not exceed the max input tokens for the [model](/for-developers/models)."
    )
    model: str = Field(
        description="ID of the model to use. Get ID for available [models](/for-developers/models)"
    )
    encoding_format: Optional[Literal["float", "base64"]] = Field(
        description="The format to return the embeddings in. Can be either `float` or `base64`.",
        default=None,
    )
    # dimensions: Optional[int] = Field(
    #     description="The number of dimensions the resulting output embeddings should have."
    # )
    user: Optional[str] = Field(
        description="A unique identifier representing your end-user",
        repr=False,
        default=None,
    )

    class Config:
        json_schema_extra = {
            "example": {
                "model": "gte-large-en-v1.5",
                "input": [
                    "My epic text number 1",
                    "My epic text number 2",
                ],
            }
        }
