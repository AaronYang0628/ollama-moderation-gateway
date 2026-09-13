"""Health and readiness endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from app.providers.ollama import OllamaProvider
from app.schemas.openai import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/readyz")
async def readyz(request: Request) -> Response:
    settings = request.app.state.settings
    provider: OllamaProvider = request.app.state.ollama_provider
    router_obj = request.app.state.model_router

    try:
        _, default_model = router_obj.resolve(settings.default_moderation_model)
    except Exception:
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "detail": "Default model configuration invalid",
                "code": "config_error",
            },
        )

    ok = await provider.health()
    if not ok:
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "detail": "Ollama is unreachable",
                "code": "ollama_unavailable",
            },
        )

    # Model availability is best-effort; cloud may not list tags
    available = await provider.model_available(default_model)
    if available is False:
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "detail": f"Default model '{default_model}' not found on Ollama",
                "code": "model_unavailable",
            },
        )

    return JSONResponse(
        status_code=200,
        content={"status": "ready", "detail": None, "code": None},
    )
