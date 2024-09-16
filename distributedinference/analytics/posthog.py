import os

from posthog import Posthog


def init_posthog(is_production: bool, is_test: bool):
    if is_production:
        api_key = os.getenv("POSTHOG_API_KEY")
    else:
        api_key = os.getenv("DEBUG_POSTHOG_API_KEY")

    posthog = Posthog(project_api_key=api_key, host="https://eu.i.posthog.com")

    if is_test:
        posthog.disabled = True

    return posthog
