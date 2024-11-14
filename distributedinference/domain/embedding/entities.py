from typing import Optional


class EmbeddingApiError(Exception):
    def __init__(self, status: int, message: Optional[str]):
        self.status = status
        self.message = message
