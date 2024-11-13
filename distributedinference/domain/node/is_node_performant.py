import settings


def execute(time_to_first_token: float, throughput: float) -> bool:
    """
    Measures how performant the node is. Currently, only the 8B model is graded as this
    is run by the end users on consumer grade GPUs.

    Initial grading is done considering max prompt token count and 1 completion token
    as this is the worst possible case for the TTFT.

    TODO: based on the benchmarks, currently the MIN_TIME_TO_FIRST_TOKEN_SEC ~= 8
    TODO: distinguish between small and big prompts

    return: True if node is performant, False otherwise
    """
    if time_to_first_token <= 0.0:
        return False

    return time_to_first_token < settings.MIN_TIME_TO_FIRST_TOKEN_SEC and throughput > 0
