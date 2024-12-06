from dataclasses import dataclass


@dataclass
class ModelPricing:
    prompt: str
    completion: str
    image: str
    request: str


@dataclass
class Model:
    id: str
    name: str
    context_length: int
    max_completion_tokens: int
    pricing: ModelPricing
