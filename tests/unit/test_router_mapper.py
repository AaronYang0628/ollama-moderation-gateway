"""Unit tests for model router and response mapper."""

from __future__ import annotations

import pytest

from app.config import Settings
from app.errors import ModelNotFoundError
from app.moderation.mapper import OpenAIResponseMapper
from app.moderation.router import ModelRouter
from app.schemas.internal import EvaluationResult
from app.schemas.openai import DEFAULT_CATEGORIES


@pytest.fixture
def settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("MODERATION_API_KEY", "x")
    return Settings()


def test_alias_resolution(settings: Settings) -> None:
    router = ModelRouter(settings)
    alias, effective = router.resolve("moderation-fast")
    assert alias == "moderation-fast"
    assert effective == "gpt-oss:20b"


def test_native_name(settings: Settings) -> None:
    router = ModelRouter(settings)
    alias, effective = router.resolve("gemma4:31b")
    assert effective == "gemma4:31b"


def test_default_model(settings: Settings) -> None:
    router = ModelRouter(settings)
    alias, effective = router.resolve(None)
    assert alias == "moderation-fast"
    assert effective == "gpt-oss:20b"


def test_unknown_model(settings: Settings) -> None:
    router = ModelRouter(settings)
    with pytest.raises(ModelNotFoundError):
        router.resolve("no-such-model")


def test_mapper_order_and_fields() -> None:
    mapper = OpenAIResponseMapper(include_applied_input_types=True)
    cats = {n: False for n in DEFAULT_CATEGORIES}
    scores = {n: 0.01 for n in DEFAULT_CATEGORIES}
    cats["harassment"] = True
    scores["harassment"] = 0.8
    ev1 = EvaluationResult(flagged=False, categories=dict(cats), category_scores=dict(scores))
    ev2 = EvaluationResult(
        flagged=True,
        categories=dict(cats),
        category_scores=dict(scores),
    )
    resp = mapper.to_response(model="moderation-fast", evaluations=[ev1, ev2])
    assert resp.id.startswith("modr-")
    assert len(resp.results) == 2
    assert resp.results[0].flagged is False
    assert resp.results[1].flagged is True
    assert resp.results[0].category_applied_input_types["sexual"] == ["text"]
