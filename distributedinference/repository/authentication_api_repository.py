from stytch import Client

import settings
from distributedinference.domain.user.entities import UserAuthenticationResponse


class AuthenticationApiRepository:

    def __init__(self):
        self._client = Client(
            project_id=settings.STYTCH_PROJECT_ID,
            secret=settings.STYTCH_SECRET,
        )

    async def signup_user(self, email: str) -> str:
        resp = await self._client.magic_links.email.login_or_create_async(
            email=email,
        )
        if not resp.user_created:
            # If not new user raise exception?
            pass
        return resp.user_id

    async def authenticate_magic_link(self, token: str) -> UserAuthenticationResponse:
        resp = await self._client.magic_links.authenticate_async(
            token=token,
            # TODO: time
            session_duration_minutes=5,
        )
        return UserAuthenticationResponse(
            provider_user_id=resp.user_id, session_token=resp.session_token
        )

    async def set_user_password(self, password: str, session_token: str) -> UserAuthenticationResponse:
        resp = await self._client.passwords.sessions.reset_async(
            password=password,
            session_token=session_token,
            # TODO: time
            session_duration_minutes=120,
        )
        return UserAuthenticationResponse(
            provider_user_id=resp.user_id, session_token=resp.session_token
        )

    async def login(self, email: str, password: str) -> UserAuthenticationResponse:
        resp = await self._client.passwords.authenticate_async(
            email=email,
            password=password,
            # TODO: time
            session_duration_minutes=24 * 60,
        )
        return UserAuthenticationResponse(
            provider_user_id=resp.user_id, session_token=resp.session_token
        )
