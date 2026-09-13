"""OpenAI-style error helpers and domain exceptions."""

from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse


class GatewayError(Exception):
    """Base error with OpenAI-compatible error payload."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int = 500,
        error_type: str = "internal_server_error",
        code: str = "internal_error",
        param: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_type = error_type
        self.code = code
        self.param = param

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": {
                "message": self.message,
                "type": self.error_type,
                "param": self.param,
                "code": self.code,
            }
        }


class InvalidRequestError(GatewayError):
    def __init__(
        self,
        message: str,
        *,
        code: str = "invalid_input",
        param: str | None = None,
        status_code: int = 400,
    ) -> None:
        super().__init__(
            message,
            status_code=status_code,
            error_type="invalid_request_error",
            code=code,
            param=param,
        )


class AuthenticationError(GatewayError):
    def __init__(self, message: str = "Invalid API key") -> None:
        super().__init__(
            message,
            status_code=401,
            error_type="authentication_error",
            code="invalid_api_key",
        )


class ModelNotFoundError(GatewayError):
    def __init__(self, model: str) -> None:
        super().__init__(
            f"Model '{model}' not found",
            status_code=404,
            error_type="invalid_request_error",
            code="model_not_found",
            param="model",
        )


class TimeoutGatewayError(GatewayError):
    def __init__(
        self,
        message: str = "Request timed out",
        *,
        code: str = "request_timeout",
        status_code: int = 408,
    ) -> None:
        super().__init__(
            message,
            status_code=status_code,
            error_type="timeout_error",
            code=code,
        )


class RateLimitError(GatewayError):
    def __init__(self, message: str = "Concurrency limit exceeded") -> None:
        super().__init__(
            message,
            status_code=429,
            error_type="rate_limit_error",
            code="concurrency_limit",
        )


class ProviderError(GatewayError):
    def __init__(
        self,
        message: str,
        *,
        code: str = "invalid_model_output",
        status_code: int = 502,
    ) -> None:
        super().__init__(
            message,
            status_code=status_code,
            error_type="provider_error",
            code=code,
        )


class ServiceUnavailableError(GatewayError):
    def __init__(
        self,
        message: str = "Ollama unavailable",
        *,
        code: str = "ollama_unavailable",
    ) -> None:
        super().__init__(
            message,
            status_code=503,
            error_type="service_unavailable",
            code=code,
        )


async def gateway_error_handler(_request: Request, exc: GatewayError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content=exc.to_dict())


async def unhandled_error_handler(_request: Request, _exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "message": "Internal server error",
                "type": "internal_server_error",
                "param": None,
                "code": "internal_error",
            }
        },
    )
