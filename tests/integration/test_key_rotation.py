"""Integration tests for multi-key rotation against mock Ollama."""

from __future__ import annotations

import httpx
import pytest
import respx
from httpx import ASGITransport, AsyncClient

from app.config import Settings, clear_settings_cache
from app.main import create_app
from app.schemas.openai import DEFAULT_CATEGORIES
from tests.conftest import make_ollama_chat_response


def _scores() -> dict[str, float]:
    return {n: 0.01 for n in DEFAULT_CATEGORIES}


@pytest.fixture
def multi_key_settings(policy_path, monkeypatch: pytest.MonkeyPatch) -> Settings:
    clear_settings_cache()
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("MODERATION_API_KEY", "test-key")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://ollama.test")
    monkeypatch.setenv("OLLAMA_API_KEYS", "key-one,key-two,key-three")
    monkeypatch.setenv("OLLAMA_API_KEY", "")
    monkeypatch.setenv("POLICY_PATH", str(policy_path))
    monkeypatch.setenv("KEY_COOLDOWN_SECONDS", "60")
    clear_settings_cache()
    return Settings()


@pytest.mark.asyncio
@respx.mock
async def test_rotates_on_429(multi_key_settings: Settings) -> None:
    seen_keys: list[str] = []

    def _side_effect(request: httpx.Request) -> httpx.Response:
        auth = request.headers.get("Authorization", "")
        seen_keys.append(auth)
        if auth == "Bearer key-one":
            return httpx.Response(429, text="rate limit")
        return httpx.Response(200, json=make_ollama_chat_response(_scores()))

    respx.post("http://ollama.test/api/chat").mock(side_effect=_side_effect)
    app = create_app(multi_key_settings)
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/v1/moderations",
                headers={"Authorization": "Bearer test-key"},
                json={"input": "hello"},
            )
    assert resp.status_code == 200
    assert "Bearer key-one" in seen_keys
    assert any(k == "Bearer key-two" for k in seen_keys)


@pytest.mark.asyncio
@respx.mock
async def test_rotates_on_401(multi_key_settings: Settings) -> None:
    calls = {"n": 0}

    def _side_effect(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        auth = request.headers.get("Authorization", "")
        if auth == "Bearer key-one":
            return httpx.Response(401, text="unauthorized")
        return httpx.Response(200, json=make_ollama_chat_response(_scores()))

    respx.post("http://ollama.test/api/chat").mock(side_effect=_side_effect)
    app = create_app(multi_key_settings)
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/v1/moderations",
                headers={"Authorization": "Bearer test-key"},
                json={"input": "hello"},
            )
    assert resp.status_code == 200
    assert calls["n"] >= 2


@pytest.mark.asyncio
@respx.mock
async def test_bearer_sent_to_cloud(multi_key_settings: Settings) -> None:
    route = respx.post("http://ollama.test/api/chat").mock(
        return_value=httpx.Response(200, json=make_ollama_chat_response(_scores()))
    )
    app = create_app(multi_key_settings)
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.post(
                "/v1/moderations",
                headers={"Authorization": "Bearer test-key"},
                json={"input": "hello"},
            )
    assert route.calls[0].request.headers["Authorization"].startswith("Bearer key-")
