"""FastAPI application entrypoint."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes_health import router as health_router
from app.api.routes_models import router as models_router
from app.api.routes_moderations import router as moderations_router
from app.config import Settings, get_settings
from app.errors import GatewayError, gateway_error_handler, unhandled_error_handler
from app.logging import setup_logging
from app.moderation.policy import load_policy
from app.moderation.router import ModelRouter
from app.moderation.service import ModerationService
from app.providers.ollama import OllamaProvider

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    setup_logging(settings.log_level)

    if not settings.moderation_api_key_list and not settings.is_production:
        logger.warning(
            "No gateway API key set — authentication is DISABLED (dev/test only)"
        )
    if settings.log_raw_input:
        logger.warning("LOG_RAW_INPUT=true — raw user input may appear in logs (HIGH RISK)")

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        provider = OllamaProvider(
            base_url=settings.ollama_base_url,
            api_keys=settings.ollama_api_key_list,
            connect_timeout=settings.ollama_connect_timeout_seconds,
            read_timeout=settings.ollama_read_timeout_seconds,
            keep_alive=settings.ollama_keep_alive,
            key_cooldown_seconds=settings.key_cooldown_seconds,
        )
        policy = load_policy(
            settings.resolve_policy_path(),
            uncertain_mode_override=settings.uncertain_mode,
        )
        model_router = ModelRouter(settings)
        service = ModerationService(
            settings=settings,
            policy=policy,
            provider=provider,
            router=model_router,
        )
        app.state.settings = settings
        app.state.ollama_provider = provider
        app.state.model_router = model_router
        app.state.moderation_service = service
        app.state.policy = policy
        logger.info(
            "Gateway started env=%s ollama_base_url=%s docs=%s keys_configured=%s",
            settings.app_env,
            settings.ollama_base_url,
            settings.enable_docs,
            provider.key_pool.size,
        )
        try:
            yield
        finally:
            await provider.aclose()

    app = FastAPI(
        title="Ollama Moderation Gateway",
        version="0.1.0",
        description=(
            "OpenAI-compatible Moderations API gateway backed by Ollama. "
            "category_scores are heuristic risk estimates from general-purpose models, "
            "NOT calibrated probabilities and NOT equivalent to OpenAI omni-moderation-latest."
        ),
        lifespan=lifespan,
        docs_url="/docs" if settings.enable_docs else None,
        redoc_url="/redoc" if settings.enable_docs else None,
        openapi_url="/openapi.json" if settings.enable_docs else None,
    )

    if settings.cors_origin_list:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origin_list,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    app.add_exception_handler(GatewayError, gateway_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)

    @app.exception_handler(RequestValidationError)
    async def validation_handler(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        errors = exc.errors()
        param = None
        code = "invalid_input"
        message = "Invalid request"
        if errors:
            err = errors[0]
            loc = err.get("loc") or ()
            if len(loc) >= 2:
                param = str(loc[-1])
            msg = str(err.get("msg", message))
            message = msg
            lower = msg.lower()
            if "multimodal" in lower or "image" in lower:
                code = "multimodal_not_supported"
            elif "too long" in lower or "max_input" in lower:
                code = "input_too_long"
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "message": message,
                    "type": "invalid_request_error",
                    "param": param,
                    "code": code,
                }
            },
        )

    app.include_router(health_router)
    app.include_router(models_router)
    app.include_router(moderations_router)
    return app


app = create_app()
