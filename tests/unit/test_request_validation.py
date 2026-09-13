"""Request validation and auth unit/API tests."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from app.config import Settings
from app.main import create_app
from app.schemas.openai import ModerationRequest


def test_empty_string_rejected() -> None:
    with pytest.raises(ValidationError):
        ModerationRequest(input="   ")


def test_empty_array_rejected() -> None:
    with pytest.raises(ValidationError):
        ModerationRequest(input=[])


def test_multimodal_object_rejected() -> None:
    with pytest.raises(ValidationError):
        ModerationRequest(input=[{"type": "image_url", "image_url": {"url": "x"}}])  # type: ignore[arg-type]


def test_mixed_types_rejected() -> None:
    with pytest.raises(ValidationError):
        ModerationRequest(input=["ok", 123])  # type: ignore[list-item]


@pytest.mark.asyncio
async def test_auth_required(test_settings: Settings) -> None:
    app = create_app(test_settings)
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/v1/moderations",
                json={"input": "hello"},
            )
            assert resp.status_code == 401
            body = resp.json()
            assert body["error"]["code"] == "invalid_api_key"


@pytest.mark.asyncio
async def test_wrong_key(test_settings: Settings) -> None:
    app = create_app(test_settings)
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/v1/moderations",
                json={"input": "hello"},
                headers={"Authorization": "Bearer wrong"},
            )
            assert resp.status_code == 401


@pytest.mark.asyncio
async def test_health_no_auth(test_settings: Settings) -> None:
    app = create_app(test_settings)
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health")
            assert resp.status_code == 200
            assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_models_list(test_settings: Settings, auth_headers: dict) -> None:
    app = create_app(test_settings)
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/v1/models", headers=auth_headers)
            assert resp.status_code == 200
            ids = {m["id"] for m in resp.json()["data"]}
            assert "moderation-fast" in ids
            assert "omni-moderation-latest" in ids


def test_moderation_api_key_list_merges(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.config import clear_settings_cache

    clear_settings_cache()
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("MODERATION_API_KEYS", " key-a ,key-b, ")
    monkeypatch.setenv("MODERATION_API_KEY", "key-a")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://ollama.test")
    monkeypatch.setenv("OLLAMA_API_KEYS", "")
    monkeypatch.setenv("OLLAMA_API_KEY", "")
    clear_settings_cache()
    settings = Settings()
    assert settings.moderation_api_key_list == ["key-a", "key-b"]


def test_production_requires_gateway_key(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.config import clear_settings_cache

    clear_settings_cache()
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("MODERATION_API_KEY", "")
    monkeypatch.setenv("MODERATION_API_KEYS", "")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://ollama.test")
    monkeypatch.setenv("OLLAMA_API_KEYS", "")
    monkeypatch.setenv("OLLAMA_API_KEY", "")
    clear_settings_cache()
    with pytest.raises(ValidationError):
        Settings()


def test_production_accepts_keys_list_only(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.config import clear_settings_cache

    clear_settings_cache()
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("MODERATION_API_KEY", "")
    monkeypatch.setenv("MODERATION_API_KEYS", "prod-key-1,prod-key-2")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://ollama.test")
    monkeypatch.setenv("OLLAMA_API_KEYS", "")
    monkeypatch.setenv("OLLAMA_API_KEY", "")
    clear_settings_cache()
    settings = Settings()
    assert settings.moderation_api_key_list == ["prod-key-1", "prod-key-2"]


@pytest.mark.asyncio
async def test_multi_key_auth_accepts_any(
    policy_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.config import clear_settings_cache

    clear_settings_cache()
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("MODERATION_API_KEY", "legacy-key")
    monkeypatch.setenv("MODERATION_API_KEYS", "key-one,key-two")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://ollama.test")
    monkeypatch.setenv("OLLAMA_API_KEYS", "")
    monkeypatch.setenv("OLLAMA_API_KEY", "")
    monkeypatch.setenv("POLICY_PATH", str(policy_path))
    monkeypatch.setenv("ENABLE_DOCS", "true")
    clear_settings_cache()
    settings = Settings()
    assert settings.moderation_api_key_list == ["key-one", "key-two", "legacy-key"]
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            for key in ("key-one", "key-two", "legacy-key"):
                resp = await client.get(
                    "/v1/models", headers={"Authorization": f"Bearer {key}"}
                )
                assert resp.status_code == 200, key
            resp = await client.get(
                "/v1/models", headers={"Authorization": "Bearer no-such-key"}
            )
            assert resp.status_code == 401
