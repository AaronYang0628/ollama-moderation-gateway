"""POST /v1/moderations"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response
from pydantic import ValidationError

from app.api.deps import get_service, require_api_key, resolve_request_id
from app.errors import InvalidRequestError
from app.moderation.service import ModerationService
from app.schemas.openai import ModerationRequest, ModerationResponse

router = APIRouter(prefix="/v1", tags=["moderations"])


@router.post("/moderations", response_model=ModerationResponse)
async def create_moderation(
    body: ModerationRequest,
    response: Response,
    _auth: Annotated[None, Depends(require_api_key)],
    service: Annotated[ModerationService, Depends(get_service)],
    request_id: Annotated[str, Depends(resolve_request_id)],
) -> ModerationResponse:
    response.headers["X-Request-ID"] = request_id
    try:
        return await service.moderate(
            input_data=body.input,
            model=body.model,
            request_id=request_id,
        )
    except ValidationError as exc:
        raise InvalidRequestError(str(exc), code="invalid_input", param="input") from exc
