from typing import List
from typing import Literal
from typing import Optional
from typing import Union

from pydantic import BaseModel
from pydantic import Field


class EmbeddingRequest(BaseModel):
    input: Union[str, List[str]] = Field(description="")
    model: str = Field(description="ID of the model to use.")
    # TODO: do we want to support base64 like openAI?
    encoding_format: Optional[Literal["float"]] = Field(
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


class EmbeddingObject(BaseModel):
    index: int = Field(
        description="The index of the embedding in the list of embeddings."
    )
    embedding: List[float] = Field(
        description="The embedding vector, which is a list of floats. The length of vector depends on the model."
    )
    object: Literal["embedding"] = Field(
        description='The object type, which is always "embedding".'
    )


class EmbeddingResponse(BaseModel):
    object: Literal["list"] = Field()
    data: List[EmbeddingObject] = Field()
    model: str = Field()
