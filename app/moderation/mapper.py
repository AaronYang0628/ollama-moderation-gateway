"""Map evaluation results to OpenAI-style responses."""

from __future__ import annotations

import uuid
from typing import Any

from app.schemas.internal import EvaluationResult
from app.schemas.openai import ModerationResponse, ModerationResult


def new_moderation_id() -> str:
    return f"modr-{uuid.uuid4().hex}"


class OpenAIResponseMapper:
    def __init__(self, *, include_applied_input_types: bool = True) -> None:
        self.include_applied_input_types = include_applied_input_types

    def to_result(self, evaluation: EvaluationResult) -> ModerationResult:
        applied: dict[str, list[str]] | None = None
        if self.include_applied_input_types:
            applied = {name: ["text"] for name in evaluation.categories}
        return ModerationResult(
            flagged=evaluation.flagged,
            categories=dict(evaluation.categories),
            category_scores={k: round(v, 6) for k, v in evaluation.category_scores.items()},
            category_applied_input_types=applied,
        )

    def to_response(
        self,
        *,
        model: str,
        evaluations: list[EvaluationResult],
        metadata: dict[str, Any] | None = None,
        response_id: str | None = None,
    ) -> ModerationResponse:
        results = [self.to_result(ev) for ev in evaluations]
        payload = ModerationResponse(
            id=response_id or new_moderation_id(),
            model=model,
            results=results,
        )
        if metadata:
            payload.metadata = metadata
        return payload
