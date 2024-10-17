from stytch import Client

import settings
from distributedinference.domain.user.entities import UserAuthenticationResponse


class AuthenticationApiRepository:

    def __init__(self):
        self._client = Client(
            project_id=settings.STYTCH_PROJECT_ID,
            secret=settings.STYTCH_SECRET,
        )

    async def signup_with_password(
        self, email: str, password: str
    ) -> UserAuthenticationResponse:
        resp = await self._client.passwords.create_async(
            email=email,
            password=password,
            session_duration_minutes=settings.SESSION_DURATION_MINUTES,
        )
        return UserAuthenticationResponse(
            provider_user_id=resp.user_id, session_token=resp.session_token
        )

    async def reset_user(self, email: str) -> str:
        resp = await self._client.magic_links.email.login_or_create_async(
            email=email,
        )
        if not resp.user_created:
            # Currently this flow can be used to reset the password,
            # since we are not checking if it's a new user
            pass
        return resp.user_id

    async def authenticate_magic_link(self, token: str) -> UserAuthenticationResponse:
        resp = await self._client.magic_links.authenticate_async(
            token=token,
            # Short duration here, since this token is just used once
            session_duration_minutes=5,
        )
        return UserAuthenticationResponse(
            provider_user_id=resp.user_id, session_token=resp.session_token
        )

    async def set_user_password(
        # Token from email redirect URL
        self,
        password: str,
        token: str,
    ) -> UserAuthenticationResponse:
        resp = await self._client.passwords.email.reset_async(
            password=password,
            token=token,
            session_duration_minutes=settings.SESSION_DURATION_MINUTES,
        )
        return UserAuthenticationResponse(
            provider_user_id=resp.user_id, session_token=resp.session_token
        )

    async def login(self, email: str, password: str) -> UserAuthenticationResponse:
        resp = await self._client.passwords.authenticate_async(
            email=email,
            password=password,
            session_duration_minutes=settings.SESSION_DURATION_MINUTES,
        )
        return UserAuthenticationResponse(
            provider_user_id=resp.user_id, session_token=resp.session_token
        )

    async def authenticate_session(
        self, session_token: str
    ) -> UserAuthenticationResponse:
        resp = await self._client.sessions.authenticate_async(
            session_token=session_token
        )
        return UserAuthenticationResponse(
            provider_user_id=resp.user.user_id, session_token=resp.session_token
        )
