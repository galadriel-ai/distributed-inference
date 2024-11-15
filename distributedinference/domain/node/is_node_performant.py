import settings


def execute(time_to_first_token: float, throughput: float, prompt_tokens: int) -> bool:
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
    if time_to_first_token <= 0.0:
        return False

    if throughput <= 0:
        return False

    if prompt_tokens < settings.SMALL_PROMPT_SIZE:
        return time_to_first_token < settings.MIN_TIME_TO_FIRST_TOKEN_SMALL_SEC
    return time_to_first_token < settings.MIN_TIME_TO_FIRST_TOKEN_BIG_SEC
