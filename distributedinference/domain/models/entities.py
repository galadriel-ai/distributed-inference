from dataclasses import dataclass


@dataclass
class ModelPricing:
    prompt: float
    completion: float
    image: float
    request: float


@dataclass
class Model:
    id: str
    name: str
    context_length: int
    max_completion_tokens: int
    pricing: ModelPricing
