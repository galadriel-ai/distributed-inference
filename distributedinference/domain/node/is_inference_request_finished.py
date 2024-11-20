from typing import Optional

from packaging import version
from openai.types import CompletionUsage

from distributedinference.domain.node.entities import ConnectedNode
from distributedinference.domain.node.entities import InferenceResponse


LMDEPLOY_NODE_VERSION = version.parse("0.0.16")


def execute(
    node: ConnectedNode,
    response: InferenceResponse,
    usage: Optional[CompletionUsage],
) -> bool:
    if (
        (not node.version or node.version < LMDEPLOY_NODE_VERSION)
        and usage is not None
        and response.chunk
        and len(response.chunk.choices) == 0
    ):
        return True
    return False
