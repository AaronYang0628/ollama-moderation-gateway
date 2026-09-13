"""Moderation orchestration service."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from app.config import Settings
from app.errors import (
    InvalidRequestError,
    ProviderError,
    ServiceUnavailableError,
    TimeoutGatewayError,
)
from app.logging import safe_log_fields
from app.moderation.mapper import OpenAIResponseMapper
from app.moderation.parser import ModelOutputParser
from app.moderation.policy import ModerationPolicy, PolicyConfig
from app.moderation.prompts import build_messages
from app.moderation.router import ModelRouter
from app.providers.ollama import OllamaProvider
from app.schemas.internal import EvaluationResult
from app.schemas.openai import ModerationResponse

logger = logging.getLogger(__name__)


class ModerationService:
    def __init__(
        self,
        *,
        settings: Settings,
        policy: PolicyConfig,
        provider: OllamaProvider,
        router: ModelRouter | None = None,
        mapper: OpenAIResponseMapper | None = None,
        parser: ModelOutputParser | None = None,
    ) -> None:
        self.settings = settings
        self.policy_config = policy
        self.policy = ModerationPolicy(policy)
        self.provider = provider
        self.router = router or ModelRouter(settings)
        self.mapper = mapper or OpenAIResponseMapper(
            include_applied_input_types=settings.include_applied_input_types
        )
        self.parser = parser or ModelOutputParser(policy.category_names())
        self._semaphore = asyncio.Semaphore(settings.max_concurrency)
        self._active = 0
        self._active_lock = asyncio.Lock()

    def _normalize_inputs(self, raw: str | list[str]) -> list[str]:
        texts = [raw] if isinstance(raw, str) else list(raw)
        if len(texts) > self.settings.max_batch_size:
            raise InvalidRequestError(
                f"Batch size {len(texts)} exceeds MAX_BATCH_SIZE={self.settings.max_batch_size}",
                code="batch_too_large",
                param="input",
            )
        for i, text in enumerate(texts):
            if len(text) > self.settings.max_input_chars:
                raise InvalidRequestError(
                    f"input[{i}] exceeds MAX_INPUT_CHARS={self.settings.max_input_chars}",
                    code="input_too_long",
                    param="input",
                )
        return texts

    def _options(self) -> dict[str, Any]:
        return {
            "temperature": self.settings.temperature,
            "top_p": self.settings.top_p,
            "top_k": self.settings.top_k,
        }

    async def _call_model(
        self,
        *,
        text: str,
        effective_model: str,
        strict_retry: bool = False,
    ) -> EvaluationResult:
        messages = build_messages(
            text,
            self.policy_config,
            prompt_version=self.settings.prompt_version,
            strict_retry=strict_retry,
        )
        schema = self.policy.response_schema()
        started = time.perf_counter()
        raw = await self.provider.chat(
            model=effective_model,
            messages=messages,
            response_schema=schema,
            options=self._options(),
            keep_alive=self.settings.ollama_keep_alive,
            thinking=self.settings.thinking,
        )
        latency_ms = (time.perf_counter() - started) * 1000.0

        message = (raw.get("message") or {}) if isinstance(raw, dict) else {}
        content = message.get("content", "")
        # Drop thinking if present
        if isinstance(message, dict) and "thinking" in message:
            message = {k: v for k, v in message.items() if k != "thinking"}

        parsed = self.parser.parse(content)
        evaluation = self.policy.evaluate(parsed)
        evaluation.effective_model = effective_model
        evaluation.latency_ms = latency_ms
        return evaluation

    async def _moderate_one(
        self, text: str, effective_model: str
    ) -> EvaluationResult:
        try:
            return await self._call_model(text=text, effective_model=effective_model)
        except ProviderError:
            # One strict retry on parse/schema failure
            logger.warning(
                "Parse failed; retrying once",
                extra=safe_log_fields(
                    effective_model=effective_model, parse_status="retry"
                ),
            )
            try:
                return await self._call_model(
                    text=text, effective_model=effective_model, strict_retry=True
                )
            except ProviderError:
                raise ProviderError(
                    "Model output invalid after retry",
                    code="invalid_model_output",
                )

    async def moderate(
        self,
        *,
        input_data: str | list[str],
        model: str | None,
        request_id: str,
    ) -> ModerationResponse:
        texts = self._normalize_inputs(input_data)
        external_model, effective_model = self.router.resolve(model)

        # Bounded concurrency via semaphore; whole-batch timeout applied below
        async def _run_all() -> list[EvaluationResult]:
            async def _one(text: str) -> EvaluationResult:
                async with self._semaphore:
                    return await self._moderate_one(text, effective_model)

            tasks = [asyncio.create_task(_one(t)) for t in texts]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            evaluations: list[EvaluationResult] = []
            for result in results:
                if isinstance(result, Exception):
                    # Fail entire batch
                    raise result
                evaluations.append(result)
            return evaluations

        started = time.perf_counter()
        try:
            evaluations = await asyncio.wait_for(
                _run_all(), timeout=self.settings.request_timeout_seconds
            )
        except TimeoutError as exc:
            raise TimeoutGatewayError(
                "Request timed out",
                code="request_timeout",
                status_code=408,
            ) from exc
        except ProviderError:
            raise
        except (ServiceUnavailableError, TimeoutGatewayError, InvalidRequestError):
            raise
        except Exception as exc:
            logger.exception("Unexpected moderation error request_id=%s", request_id)
            raise ServiceUnavailableError(str(exc)[:200]) from exc

        latency_ms = (time.perf_counter() - started) * 1000.0
        flagged_count = sum(1 for e in evaluations if e.flagged)
        logger.info(
            "moderation_complete %s",
            safe_log_fields(
                request_id=request_id,
                route="/v1/moderations",
                model_alias=external_model,
                effective_model=effective_model,
                input_count=len(texts),
                input_chars_total=sum(len(t) for t in texts),
                latency_ms=round(latency_ms, 2),
                parse_status="ok",
                flagged_count=flagged_count,
                fallback_used=False,
            ),
        )

        metadata = None
        if self.settings.expose_backend_metadata:
            metadata = {
                "policy_version": self.policy_config.version,
                "effective_model": effective_model,
                "latency_ms": round(latency_ms, 2),
                "request_id": request_id,
            }

        return self.mapper.to_response(
            model=external_model,
            evaluations=evaluations,
            metadata=metadata,
        )
