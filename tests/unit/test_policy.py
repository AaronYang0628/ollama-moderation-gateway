"""Unit tests for policy evaluation."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.errors import InvalidRequestError
from app.moderation.policy import CategoryConfig, ModerationPolicy, PolicyConfig, load_policy
from app.schemas.internal import ParsedModelOutput
from app.schemas.openai import DEFAULT_CATEGORIES


def test_load_policy(policy_path: Path) -> None:
    policy = load_policy(policy_path)
    assert policy.version == "v1"
    assert "sexual" in policy.categories
    assert policy.threshold_for("sexual/minors") == 0.30


def test_threshold_flagging() -> None:
    cfg = PolicyConfig(
        categories={
            "harassment": CategoryConfig(threshold=0.55),
            "violence": CategoryConfig(threshold=0.55),
        }
    )
    policy = ModerationPolicy(cfg)
    parsed = ParsedModelOutput(
        category_scores={"harassment": 0.56, "violence": 0.1},
        uncertain=False,
    )
    result = policy.evaluate(parsed)
    assert result.categories["harassment"] is True
    assert result.categories["violence"] is False
    assert result.flagged is True


def test_uncertain_flag_mode() -> None:
    cfg = PolicyConfig(
        uncertain_mode="flag",
        categories={n: CategoryConfig(threshold=0.9) for n in DEFAULT_CATEGORIES},
    )
    policy = ModerationPolicy(cfg)
    parsed = ParsedModelOutput(
        category_scores={n: 0.0 for n in DEFAULT_CATEGORIES},
        uncertain=True,
    )
    result = policy.evaluate(parsed)
    assert result.flagged is True


def test_uncertain_allow_mode() -> None:
    cfg = PolicyConfig(
        uncertain_mode="allow",
        categories={n: CategoryConfig(threshold=0.9) for n in DEFAULT_CATEGORIES},
    )
    policy = ModerationPolicy(cfg)
    parsed = ParsedModelOutput(
        category_scores={n: 0.0 for n in DEFAULT_CATEGORIES},
        uncertain=True,
    )
    result = policy.evaluate(parsed)
    assert result.flagged is False


def test_uncertain_error_mode() -> None:
    cfg = PolicyConfig(
        uncertain_mode="error",
        categories={n: CategoryConfig() for n in DEFAULT_CATEGORIES},
    )
    policy = ModerationPolicy(cfg)
    parsed = ParsedModelOutput(
        category_scores={n: 0.0 for n in DEFAULT_CATEGORIES},
        uncertain=True,
    )
    with pytest.raises(InvalidRequestError) as exc:
        policy.evaluate(parsed)
    assert exc.value.code == "uncertain_classification"


def test_disabled_category_not_flagged() -> None:
    cfg = PolicyConfig(
        categories={
            "harassment": CategoryConfig(enabled=False, threshold=0.1),
            "violence": CategoryConfig(threshold=0.5),
        }
    )
    policy = ModerationPolicy(cfg)
    parsed = ParsedModelOutput(
        category_scores={"harassment": 0.99, "violence": 0.1},
        uncertain=False,
    )
    result = policy.evaluate(parsed)
    assert result.categories["harassment"] is False
    assert result.flagged is False
