import os

from posthog import Posthog


def init_posthog(is_production: bool):
    if is_production:
        api_key = os.getenv("POSTHOG_API_KEY")
    else:
        api_key = os.getenv("DEBUG_POSTHOG_API_KEY")

    posthog = Posthog(project_api_key=api_key, host="https://eu.i.posthog.com")
    posthog.debug = not is_production
    return posthog
