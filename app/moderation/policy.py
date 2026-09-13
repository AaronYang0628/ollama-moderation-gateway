"""Policy loading and evaluation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from app.errors import InvalidRequestError
from app.schemas.internal import EvaluationResult, ParsedModelOutput
from app.schemas.openai import DEFAULT_CATEGORIES


class CategoryConfig(BaseModel):
    enabled: bool = True
    threshold: float = 0.5
    description: str = ""
    positive_example: str = ""
    negative_example: str = ""


class PolicyConfig(BaseModel):
    version: str = "v1"
    uncertain_mode: str = "flag"
    default_threshold: float = 0.5
    categories: dict[str, CategoryConfig] = Field(default_factory=dict)

    def category_names(self) -> list[str]:
        if self.categories:
            return list(self.categories.keys())
        return list(DEFAULT_CATEGORIES)

    def threshold_for(self, name: str) -> float:
        cat = self.categories.get(name)
        if cat is None:
            return self.default_threshold
        return cat.threshold

    def is_enabled(self, name: str) -> bool:
        cat = self.categories.get(name)
        if cat is None:
            return True
        return cat.enabled


def load_policy(path: Path, *, uncertain_mode_override: str | None = None) -> PolicyConfig:
    if not path.exists():
        # Fall back to defaults matching OpenAI category set
        policy = PolicyConfig(
            categories={name: CategoryConfig() for name in DEFAULT_CATEGORIES}
        )
    else:
        with path.open("r", encoding="utf-8") as fh:
            raw: dict[str, Any] = yaml.safe_load(fh) or {}
        cats = raw.get("categories") or {}
        parsed_cats: dict[str, CategoryConfig] = {}
        for name, cfg in cats.items():
            if isinstance(cfg, dict):
                parsed_cats[name] = CategoryConfig(**cfg)
            else:
                parsed_cats[name] = CategoryConfig()
        policy = PolicyConfig(
            version=str(raw.get("version", "v1")),
            uncertain_mode=str(raw.get("uncertain_mode", "flag")),
            default_threshold=float(raw.get("default_threshold", 0.5)),
            categories=parsed_cats,
        )
    if uncertain_mode_override:
        policy.uncertain_mode = uncertain_mode_override
    return policy


class ModerationPolicy:
    def __init__(self, config: PolicyConfig) -> None:
        self.config = config

    def evaluate(self, parsed: ParsedModelOutput) -> EvaluationResult:
        category_names = self.config.category_names()
        scores: dict[str, float] = {}
        categories: dict[str, bool] = {}

        for name in category_names:
            raw_score = parsed.category_scores.get(name, 0.0)
            # Clamp already validated to [0,1]; missing -> 0.0
            score = float(raw_score)
            scores[name] = score
            if not self.config.is_enabled(name):
                categories[name] = False
                continue
            categories[name] = score >= self.config.threshold_for(name)

        flagged = any(categories.values())

        if parsed.uncertain:
            mode = self.config.uncertain_mode
            if mode == "flag":
                flagged = True
            elif mode == "allow":
                pass  # keep score-based flagged
            elif mode == "error":
                raise InvalidRequestError(
                    "Model reported uncertain classification",
                    code="uncertain_classification",
                    param=None,
                    status_code=502,
                )
            else:
                flagged = True

        return EvaluationResult(
            flagged=flagged,
            categories=categories,
            category_scores=scores,
            uncertain=parsed.uncertain,
        )

    def response_schema(self) -> dict[str, Any]:
        """JSON Schema sent to Ollama format field."""
        props = {
            name: {"type": "number", "minimum": 0, "maximum": 1}
            for name in self.config.category_names()
        }
        return {
            "type": "object",
            "properties": {
                "category_scores": {
                    "type": "object",
                    "properties": props,
                    "required": list(props.keys()),
                    "additionalProperties": False,
                },
                "uncertain": {"type": "boolean"},
            },
            "required": ["category_scores", "uncertain"],
            "additionalProperties": False,
        }
