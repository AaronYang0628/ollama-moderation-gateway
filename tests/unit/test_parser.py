"""Unit tests for model output parser."""

from __future__ import annotations

import json

import pytest

from app.errors import ProviderError
from app.moderation.parser import ModelOutputParser, extract_json_text
from app.schemas.openai import DEFAULT_CATEGORIES


@pytest.fixture
def parser() -> ModelOutputParser:
    return ModelOutputParser()


def _scores(**overrides: float) -> dict[str, float]:
    base = {n: 0.0 for n in DEFAULT_CATEGORIES}
    base.update(overrides)
    return base


def test_parse_clean_json(parser: ModelOutputParser) -> None:
    raw = json.dumps({"category_scores": _scores(harassment=0.7), "uncertain": False})
    out = parser.parse(raw)
    assert out.category_scores["harassment"] == 0.7
    assert out.uncertain is False


def test_parse_markdown_wrapped(parser: ModelOutputParser) -> None:
    inner = json.dumps({"category_scores": _scores(), "uncertain": False})
    raw = f"```json\n{inner}\n```"
    out = parser.parse(raw)
    assert out.uncertain is False


def test_missing_category_scores(parser: ModelOutputParser) -> None:
    with pytest.raises(ProviderError):
        parser.parse(json.dumps({"uncertain": False}))


def test_score_out_of_range(parser: ModelOutputParser) -> None:
    with pytest.raises(ProviderError):
        parser.parse(
            json.dumps({"category_scores": _scores(harassment=1.5), "uncertain": False})
        )


def test_nan_score(parser: ModelOutputParser) -> None:
    with pytest.raises(ProviderError):
        parser.parse({"category_scores": {"harassment": float("nan")}, "uncertain": False})


def test_string_score_coerced(parser: ModelOutputParser) -> None:
    scores = _scores()
    scores["harassment"] = "0.42"  # type: ignore[assignment]
    out = parser.parse(json.dumps({"category_scores": scores, "uncertain": False}))
    assert out.category_scores["harassment"] == pytest.approx(0.42)


def test_boolean_score_rejected(parser: ModelOutputParser) -> None:
    scores = _scores()
    scores["harassment"] = True  # type: ignore[assignment]
    with pytest.raises(ProviderError):
        parser.parse(json.dumps({"category_scores": scores, "uncertain": False}))


def test_non_json_rejected(parser: ModelOutputParser) -> None:
    with pytest.raises(ProviderError):
        parser.parse("not json at all")


def test_extract_from_noise() -> None:
    text = 'Sure! Here you go: {"category_scores": {"a": 0.1}, "uncertain": false} thanks'
    extracted = extract_json_text(text)
    assert extracted.startswith("{")
