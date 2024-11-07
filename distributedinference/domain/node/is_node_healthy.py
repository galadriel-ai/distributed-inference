import settings


def execute(time_to_first_token: float, throughput: float) -> bool:
    return time_to_first_token < settings.MIN_TIME_TO_FIRST_TOKEN_SEC and throughput > 0
