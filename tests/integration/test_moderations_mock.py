"""Integration tests with mocked Ollama HTTP API."""

from __future__ import annotations

import json

import httpx
import pytest
import respx
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.main import create_app
from app.schemas.openai import DEFAULT_CATEGORIES
from tests.conftest import make_ollama_chat_response


def _scores(**overrides: float) -> dict[str, float]:
    base = {n: 0.01 for n in DEFAULT_CATEGORIES}
    base.update(overrides)
    return base


@pytest.fixture
def gateway(test_settings: Settings):
    return create_app(test_settings)


async def _client(app):
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


@pytest.mark.asyncio
@respx.mock
async def test_single_moderation_success(
    gateway, auth_headers: dict, zero_scores: dict
) -> None:
    route = respx.post("http://ollama.test/api/chat").mock(
        return_value=httpx.Response(
            200, json=make_ollama_chat_response(zero_scores)
        )
    )
    async with gateway.router.lifespan_context(gateway):
        transport = ASGITransport(app=gateway)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/v1/moderations",
                headers=auth_headers,
                json={"input": "hello world", "model": "moderation-fast"},
            )
    assert resp.status_code == 200
    body = resp.json()
    assert body["model"] == "moderation-fast"
    assert body["id"].startswith("modr-")
    assert len(body["results"]) == 1
    assert body["results"][0]["flagged"] is False
    assert "category_scores" in body["results"][0]
    assert "categories" in body["results"][0]
    assert route.called
    sent = json.loads(route.calls[0].request.content)
    assert sent["stream"] is False
    assert sent["model"] == "gpt-oss:20b"
    assert "format" in sent
    assert sent["format"]["type"] == "object"
    assert sent["messages"][0]["role"] == "system"
    assert "<content>" in sent["messages"][1]["content"]


@pytest.mark.asyncio
@respx.mock
async def test_batch_preserves_order(
    gateway, auth_headers: dict, zero_scores: dict, high_harassment_scores: dict
) -> None:
    def _side_effect(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        user = payload["messages"][1]["content"]
        if "BAD" in user:
            return httpx.Response(
                200, json=make_ollama_chat_response(high_harassment_scores)
            )
        return httpx.Response(200, json=make_ollama_chat_response(zero_scores))

    respx.post("http://ollama.test/api/chat").mock(side_effect=_side_effect)
    async with gateway.router.lifespan_context(gateway):
        transport = ASGITransport(app=gateway)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/v1/moderations",
                headers=auth_headers,
                json={"input": ["safe one", "BAD text", "safe two"]},
            )
    assert resp.status_code == 200
    results = resp.json()["results"]
    assert len(results) == 3
    assert results[0]["flagged"] is False
    assert results[1]["flagged"] is True
    assert results[2]["flagged"] is False


@pytest.mark.asyncio
@respx.mock
async def test_parse_failure_retries_once_then_502(
    gateway, auth_headers: dict
) -> None:
    route = respx.post("http://ollama.test/api/chat").mock(
        return_value=httpx.Response(
            200,
            json={
                "message": {"role": "assistant", "content": "NOT JSON"},
                "done": True,
            },
        )
    )
    async with gateway.router.lifespan_context(gateway):
        transport = ASGITransport(app=gateway)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/v1/moderations",
                headers=auth_headers,
                json={"input": "hello"},
            )
    assert resp.status_code == 502
    assert resp.json()["error"]["code"] == "invalid_model_output"
    assert route.call_count == 2  # initial + one retry


@pytest.mark.asyncio
@respx.mock
async def test_retry_succeeds_on_second_attempt(
    gateway, auth_headers: dict, zero_scores: dict
) -> None:
    responses = [
        httpx.Response(
            200,
            json={"message": {"role": "assistant", "content": "broken"}, "done": True},
        ),
        httpx.Response(200, json=make_ollama_chat_response(zero_scores)),
    ]
    route = respx.post("http://ollama.test/api/chat").mock(side_effect=responses)
    async with gateway.router.lifespan_context(gateway):
        transport = ASGITransport(app=gateway)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/v1/moderations",
                headers=auth_headers,
                json={"input": "hello"},
            )
    assert resp.status_code == 200
    assert resp.json()["results"][0]["flagged"] is False
    assert route.call_count == 2


@pytest.mark.asyncio
@respx.mock
async def test_ollama_connection_error_503(gateway, auth_headers: dict) -> None:
    respx.post("http://ollama.test/api/chat").mock(
        side_effect=httpx.ConnectError("fail")
    )
    async with gateway.router.lifespan_context(gateway):
        transport = ASGITransport(app=gateway)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/v1/moderations",
                headers=auth_headers,
                json={"input": "hello"},
            )
    assert resp.status_code == 503
    assert resp.json()["error"]["code"] == "ollama_unavailable"


@pytest.mark.asyncio
@respx.mock
async def test_ollama_timeout_504(gateway, auth_headers: dict) -> None:
    respx.post("http://ollama.test/api/chat").mock(
        side_effect=httpx.ReadTimeout("timeout")
    )
    async with gateway.router.lifespan_context(gateway):
        transport = ASGITransport(app=gateway)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/v1/moderations",
                headers=auth_headers,
                json={"input": "hello"},
            )
    assert resp.status_code == 504
    assert resp.json()["error"]["code"] == "ollama_timeout"


@pytest.mark.asyncio
@respx.mock
async def test_model_not_found_404(gateway, auth_headers: dict) -> None:
    async with gateway.router.lifespan_context(gateway):
        transport = ASGITransport(app=gateway)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/v1/moderations",
                headers=auth_headers,
                json={"input": "hello", "model": "does-not-exist"},
            )
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "model_not_found"


@pytest.mark.asyncio
@respx.mock
async def test_input_too_long(gateway, auth_headers: dict, test_settings: Settings) -> None:
    async with gateway.router.lifespan_context(gateway):
        transport = ASGITransport(app=gateway)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/v1/moderations",
                headers=auth_headers,
                json={"input": "x" * (test_settings.max_input_chars + 1)},
            )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "input_too_long"


@pytest.mark.asyncio
@respx.mock
async def test_readyz_ok(gateway) -> None:
    respx.get("http://ollama.test/api/tags").mock(
        return_value=httpx.Response(
            200,
            json={"models": [{"name": "gpt-oss:20b"}]},
        )
    )
    async with gateway.router.lifespan_context(gateway):
        transport = ASGITransport(app=gateway)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/readyz")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ready"


@pytest.mark.asyncio
@respx.mock
async def test_readyz_unavailable(gateway) -> None:
    respx.get("http://ollama.test/api/tags").mock(side_effect=httpx.ConnectError("x"))
    respx.get("http://ollama.test/").mock(side_effect=httpx.ConnectError("x"))
    async with gateway.router.lifespan_context(gateway):
        transport = ASGITransport(app=gateway)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/readyz")
    assert resp.status_code == 503
