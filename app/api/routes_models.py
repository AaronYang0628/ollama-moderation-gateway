"""GET /v1/models"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.api.deps import require_api_key
from app.config import Settings
from app.schemas.openai import ModelInfo, ModelListResponse

router = APIRouter(prefix="/v1", tags=["models"])


@router.get("/models", response_model=ModelListResponse)
async def list_models(
    request: Request,
    _auth: Annotated[None, Depends(require_api_key)],
) -> ModelListResponse:
    settings: Settings = request.app.state.settings
    data = [
        ModelInfo(id=model_id)
        for model_id in settings.external_model_ids
    ]
    return ModelListResponse(data=data)
