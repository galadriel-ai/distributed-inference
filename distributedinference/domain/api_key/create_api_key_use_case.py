import datetime
import secrets

from distributedinference.domain.api_key.entities import CreatedApiKey
from distributedinference.domain.user.entities import User
from distributedinference.repository.user_repository import UserRepository

from distributedinference.service import utils


async def execute(user: User, repo: UserRepository) -> CreatedApiKey:
    api_key = _generate_api_key()
    # Do not need high accuracy here
    approx_created_at = utils.to_response_date_format(
        datetime.datetime.now(datetime.UTC)
    )
    api_key_id = await repo.insert_api_key(user.uid, api_key)
    return CreatedApiKey(
        api_key_id=api_key_id,
        api_key=api_key,
        created_at=approx_created_at,
    )


def _generate_api_key():
    def is_last_4_digits_alpha(_secret):
        return (
            _secret[-1].isalpha()
            and _secret[-2].isalpha()
            and _secret[-3].isalpha()
            and _secret[-4].isalpha()
        )

    while True:
        secret = secrets.token_urlsafe(36)
        if secret[0].isalpha() and is_last_4_digits_alpha(secret):
            return "gal-" + secret
