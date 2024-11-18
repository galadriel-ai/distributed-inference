from uuid import UUID

import settings
from distributedinference import api_logger

logger = api_logger.get()


def execute(
    time_to_first_token: float,
    throughput: float,
    prompt_tokens: int,
    model: str,
    node_uid: UUID,
) -> bool:
    """
    Measures how performant the node is. Currently, only the 8B model is graded as this
    is run by the end users on consumer grade GPUs.

    TODO: distinguish between small and big prompts - naive solution is that small
     prompts are less than 1k prompt tokens and big otherwise

    Initial max grading is done considering max prompt token count and 1 completion
    token as this is the worst possible case for the TTFT. This value is:
    `settings.MIN_TIME_TO_FIRST_TOKEN_BIG_SEC`
    For small tokens size of `settings.SMALL_PROMPT_SIZE` the value is:
    `MIN_TIME_TO_FIRST_TOKEN_SMALL_SEC`

    return: True if node is performant, False otherwise
    """
    logger.debug(
        f"is_node_performant, ttft: {time_to_first_token}, throughput: {throughput}, "
        f"prompt_tokens: {prompt_tokens}, model:{model}, node_uid: {node_uid}"
    )
    if not _is_check_required(model):
        return True

    if time_to_first_token <= 0.0:
        return False

    if throughput <= 0:
        return False

    if prompt_tokens < settings.SMALL_PROMPT_SIZE:
        return time_to_first_token < settings.MIN_TIME_TO_FIRST_TOKEN_SMALL_SEC
    return time_to_first_token < settings.MIN_TIME_TO_FIRST_TOKEN_BIG_SEC


def _is_check_required(model: str) -> bool:
    model_config = settings.SUPPORTED_MODELS.get(model)
    if model_config:
        return model_config.get("benchmark_required")
    return False
