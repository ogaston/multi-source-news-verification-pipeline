"""Username/password auth for SQLAdmin."""

import os
import secrets

from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request


class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        username = form.get("username")
        password = form.get("password")
        expected_user = os.environ.get("ADMIN_USERNAME", "")
        expected_pass = os.environ.get("ADMIN_PASSWORD", "")
        if not expected_user or not expected_pass:
            return False
        username_ok = (
            isinstance(username, str)
            and len(username) == len(expected_user)
            and secrets.compare_digest(username, expected_user)
        )
        password_ok = (
            isinstance(password, str)
            and len(password) == len(expected_pass)
            and secrets.compare_digest(password, expected_pass)
        )
        if not (username_ok and password_ok):
            return False
        request.session.update({"authenticated": True})
        return True

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        return bool(request.session.get("authenticated"))
