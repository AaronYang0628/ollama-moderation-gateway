"""Shared pytest fixtures."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import Settings, clear_settings_cache
from app.main import create_app
from app.schemas.openai import DEFAULT_CATEGORIES


@pytest.fixture
def policy_path() -> Path:
    return Path(__file__).resolve().parents[1] / "configs" / "policy.yaml"


@pytest.fixture
def zero_scores() -> dict[str, float]:
    return {name: 0.01 for name in DEFAULT_CATEGORIES}


@pytest.fixture
def high_harassment_scores(zero_scores: dict[str, float]) -> dict[str, float]:
    scores = dict(zero_scores)
    scores["harassment"] = 0.9
    scores["harassment/threatening"] = 0.8
    return scores


def make_ollama_chat_response(
    scores: dict[str, float],
    *,
    uncertain: bool = False,
    wrap_markdown: bool = False,
) -> dict[str, Any]:
    content_obj = {"category_scores": scores, "uncertain": uncertain}
    content = json.dumps(content_obj)
    if wrap_markdown:
        content = f"```json\n{content}\n```"
    return {
        "model": "gpt-oss:20b",
        "message": {"role": "assistant", "content": content},
        "done": True,
    }


@pytest.fixture
def test_settings(policy_path: Path, monkeypatch: pytest.MonkeyPatch) -> Settings:
    clear_settings_cache()
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("MODERATION_API_KEY", "test-key")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://ollama.test")
    monkeypatch.setenv("OLLAMA_API_KEYS", "")
    monkeypatch.setenv("OLLAMA_API_KEY", "")
    monkeypatch.setenv("POLICY_PATH", str(policy_path))
    monkeypatch.setenv("ENABLE_DOCS", "true")
    monkeypatch.setenv("MAX_CONCURRENCY", "4")
    monkeypatch.setenv("KEY_COOLDOWN_SECONDS", "1")
    clear_settings_cache()
    return Settings()


@pytest.fixture
async def app_client(test_settings: Settings):
    app = create_app(test_settings)
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client, app


@pytest.fixture
def auth_headers() -> dict[str, str]:
    return {"Authorization": "Bearer test-key"}
