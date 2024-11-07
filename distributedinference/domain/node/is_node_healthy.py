import settings


def execute(time_to_first_token: float, throughput: float) -> bool:
    print("is node healthy, time_to_first_token:", time_to_first_token, "throughput:", throughput)
    return time_to_first_token < settings.MIN_TIME_TO_FIRST_TOKEN_SEC and throughput > 0
