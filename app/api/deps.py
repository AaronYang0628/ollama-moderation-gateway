"""FastAPI dependencies: auth, request id, service access."""

from __future__ import annotations

import secrets
import uuid
from typing import Annotated

from fastapi import Header, Request

from app.config import Settings
from app.errors import AuthenticationError
from app.moderation.service import ModerationService


def get_settings_dep(request: Request) -> Settings:
    return request.app.state.settings


def get_service(request: Request) -> ModerationService:
    return request.app.state.moderation_service


async def require_api_key(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    settings: Settings = request.app.state.settings
    expected = settings.moderation_api_key
    if not expected:
        # Auth disabled (dev/test only)
        return
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AuthenticationError()
    token = authorization.split(" ", 1)[1].strip()
    if not secrets.compare_digest(token, expected):
        raise AuthenticationError()


def resolve_request_id(
    x_request_id: Annotated[str | None, Header()] = None,
) -> str:
    if x_request_id and x_request_id.strip():
        # Basic sanitization — reject overly long / control chars
        rid = x_request_id.strip()[:128]
        if all(c.isprintable() for c in rid):
            return rid
    return str(uuid.uuid4())
