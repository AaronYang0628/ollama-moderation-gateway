"""Internal schemas for model output and evaluation."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ModelCategoryScores(BaseModel):
    """Raw scores returned by the model (may be partial)."""

    model_config = ConfigDict(extra="allow")

    scores: dict[str, float] = Field(default_factory=dict)


class ParsedModelOutput(BaseModel):
    category_scores: dict[str, float]
    uncertain: bool = False

    @field_validator("category_scores")
    @classmethod
    def _validate_scores(cls, v: dict[str, Any]) -> dict[str, float]:
        cleaned: dict[str, float] = {}
        for key, value in v.items():
            if isinstance(value, bool):
                raise ValueError(f"score for '{key}' must be a number, not boolean")
            if isinstance(value, str):
                try:
                    value = float(value)
                except ValueError as exc:
                    raise ValueError(f"score for '{key}' is not a number") from exc
            if not isinstance(value, (int, float)):
                raise ValueError(f"score for '{key}' must be a number")
            if value != value:  # NaN
                raise ValueError(f"score for '{key}' is NaN")
            if value < 0 or value > 1:
                raise ValueError(f"score for '{key}' out of range [0,1]: {value}")
            cleaned[key] = float(value)
        return cleaned


class EvaluationResult(BaseModel):
    flagged: bool
    categories: dict[str, bool]
    category_scores: dict[str, float]
    uncertain: bool = False
    effective_model: str | None = None
    latency_ms: float | None = None
