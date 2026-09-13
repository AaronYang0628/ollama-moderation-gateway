"""Parse and validate model structured output."""

from __future__ import annotations

import json
import math
import re
from typing import Any

from app.errors import ProviderError
from app.schemas.internal import ParsedModelOutput
from app.schemas.openai import DEFAULT_CATEGORIES

_JSON_OBJECT_RE = re.compile(r"\{[\s\S]*\}")


def extract_json_text(raw: str) -> str:
    """Extract a JSON object from model content that may include wrappers."""
    text = raw.strip()
    if not text:
        raise ProviderError("Empty model output", code="invalid_model_output")

    # Strip markdown fences
    if text.startswith("```"):
        lines = text.split("\n")
        # drop first fence line and optional last fence
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    # Direct parse attempt
    if text.startswith("{"):
        return text

    match = _JSON_OBJECT_RE.search(text)
    if match:
        return match.group(0)

    raise ProviderError("No JSON object found in model output", code="invalid_model_output")


def _coerce_score(value: Any, key: str) -> float:
    if isinstance(value, bool):
        raise ProviderError(
            f"Invalid score type for '{key}'", code="invalid_model_output"
        )
    if isinstance(value, str):
        try:
            value = float(value)
        except ValueError as exc:
            raise ProviderError(
                f"Non-numeric score for '{key}'", code="invalid_model_output"
            ) from exc
    if not isinstance(value, (int, float)):
        raise ProviderError(
            f"Invalid score type for '{key}'", code="invalid_model_output"
        )
    fval = float(value)
    if math.isnan(fval) or math.isinf(fval):
        raise ProviderError(
            f"Non-finite score for '{key}'", code="invalid_model_output"
        )
    if fval < 0.0 or fval > 1.0:
        raise ProviderError(
            f"Score out of range for '{key}'", code="invalid_model_output"
        )
    return fval


class ModelOutputParser:
    def __init__(self, category_names: list[str] | None = None) -> None:
        self.category_names = category_names or list(DEFAULT_CATEGORIES)

    def parse(self, raw_content: str | dict[str, Any]) -> ParsedModelOutput:
        if isinstance(raw_content, dict):
            data = raw_content
        else:
            try:
                json_text = extract_json_text(raw_content)
                data = json.loads(json_text)
            except json.JSONDecodeError as exc:
                raise ProviderError(
                    "Model output is not valid JSON", code="invalid_model_output"
                ) from exc

        if not isinstance(data, dict):
            raise ProviderError(
                "Model output must be a JSON object", code="invalid_model_output"
            )

        if "category_scores" not in data:
            raise ProviderError(
                "Missing category_scores in model output", code="invalid_model_output"
            )

        raw_scores = data["category_scores"]
        if not isinstance(raw_scores, dict):
            raise ProviderError(
                "category_scores must be an object", code="invalid_model_output"
            )

        scores: dict[str, float] = {}
        for key, value in raw_scores.items():
            scores[str(key)] = _coerce_score(value, str(key))

        # Ensure all expected categories present (fill missing with 0)
        for name in self.category_names:
            if name not in scores:
                scores[name] = 0.0

        uncertain = data.get("uncertain", False)
        if not isinstance(uncertain, bool):
            if isinstance(uncertain, str):
                uncertain = uncertain.lower() in {"true", "1", "yes"}
            else:
                uncertain = bool(uncertain)

        try:
            return ParsedModelOutput(category_scores=scores, uncertain=uncertain)
        except Exception as exc:
            raise ProviderError(
                f"Model output validation failed: {exc}", code="invalid_model_output"
            ) from exc
