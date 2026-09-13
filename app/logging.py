"""Structured logging with secret and input redaction."""

from __future__ import annotations

import logging
import re
import sys
from typing import Any

SECRET_PATTERNS = [
    re.compile(r"(Bearer\s+)([A-Za-z0-9._\-]+)", re.IGNORECASE),
    re.compile(r"(api[_-]?key[\"']?\s*[:=]\s*[\"']?)([^\"'\s,]+)", re.IGNORECASE),
    re.compile(r"(OLLAMA_API_KEY[S]?[\"']?\s*[:=]\s*[\"']?)([^\"'\s,]+)", re.IGNORECASE),
    re.compile(r"(MODERATION_API_KEY[\"']?\s*[:=]\s*[\"']?)([^\"'\s,]+)", re.IGNORECASE),
]


def redact_secrets(text: str) -> str:
    result = text
    for pattern in SECRET_PATTERNS:
        result = pattern.sub(r"\1[REDACTED]", result)
    return result


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = redact_secrets(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    k: redact_secrets(v) if isinstance(v, str) else v
                    for k, v in record.args.items()
                }
            elif isinstance(record.args, tuple):
                record.args = tuple(
                    redact_secrets(a) if isinstance(a, str) else a for a in record.args
                )
        return True


def setup_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    root.handlers.clear()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s [%(name)s] %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    )
    handler.addFilter(RedactingFilter())
    root.addHandler(handler)
    root.setLevel(level.upper())


def safe_log_fields(
    *,
    request_id: str | None = None,
    route: str | None = None,
    model_alias: str | None = None,
    effective_model: str | None = None,
    input_count: int | None = None,
    input_chars_total: int | None = None,
    latency_ms: float | None = None,
    ollama_status: str | None = None,
    parse_status: str | None = None,
    flagged_count: int | None = None,
    fallback_used: bool | None = None,
    error_code: str | None = None,
) -> dict[str, Any]:
    """Build a structured log dict without raw input or secrets."""
    data: dict[str, Any] = {}
    for key, value in {
        "request_id": request_id,
        "route": route,
        "model_alias": model_alias,
        "effective_model": effective_model,
        "input_count": input_count,
        "input_chars_total": input_chars_total,
        "latency_ms": latency_ms,
        "ollama_status": ollama_status,
        "parse_status": parse_status,
        "flagged_count": flagged_count,
        "fallback_used": fallback_used,
        "error_code": error_code,
    }.items():
        if value is not None:
            data[key] = value
    return data
