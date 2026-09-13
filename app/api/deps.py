"""FastAPI dependencies: auth, request id, service access."""

from __future__ import annotations

import hashlib
import hmac
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
    expected_keys = settings.moderation_api_key_list
    if not expected_keys:
        # Auth disabled (dev/test only)
        return
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AuthenticationError()
    token = authorization.split(" ", 1)[1].strip()
    # Compare against every configured key (no early return) using equal-length
    # SHA-256 digests so length mismatches cannot skip the constant-time step.
    token_digest = hashlib.sha256(token.encode("utf-8")).digest()
    matched = False
    for key in expected_keys:
        key_digest = hashlib.sha256(key.encode("utf-8")).digest()
        if hmac.compare_digest(token_digest, key_digest):
            matched = True
    if not matched:
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
