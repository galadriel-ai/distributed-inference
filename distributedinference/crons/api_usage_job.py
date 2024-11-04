import random
from urllib.parse import urljoin

import openai

import settings
from distributedinference import api_logger

MAX_REQUESTS = 22

logger = api_logger.get()


async def execute():
    if not settings.TESTING_API_KEY:
        logger.warning("TESTING_API_KEY env variable not set, exiting")
    client = openai.AsyncOpenAI(
        base_url=urljoin(_get_api_base_url(), "/v1"), api_key=settings.TESTING_API_KEY
    )
    for _ in range(random.randint(0, MAX_REQUESTS)):
        await client.chat.completions.create(
            model="neuralmagic/Meta-Llama-3.1-8B-Instruct-FP8",
            temperature=0,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Respond with one word!"},
            ],
        )


def _get_api_base_url():
    if settings.is_production():
        base_url = settings.API_BASE_URL
        if base_url.endswith("/"):
            base_url = base_url[:-1]
        return base_url
    base_url = settings.API_BASE_URL
    if base_url.endswith("/"):
        base_url = base_url[:-1]
    return f"{base_url}:{settings.API_PORT}"
