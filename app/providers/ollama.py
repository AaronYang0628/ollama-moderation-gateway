"""Ollama HTTP provider with multi-key pool and rotation."""

from __future__ import annotations

import asyncio
import itertools
import logging
import time
from typing import Any

import httpx

from app.errors import ProviderError, ServiceUnavailableError, TimeoutGatewayError

logger = logging.getLogger(__name__)

# Status codes that trigger key rotation / cooldown
ROTATE_STATUS_CODES = {401, 403, 429}


class KeyPool:
    """Round-robin API key pool with short per-key cooldown on quota/auth failures."""

    def __init__(self, keys: list[str], cooldown_seconds: float = 30.0) -> None:
        self._keys = list(keys)
        self._cooldown_seconds = cooldown_seconds
        self._cooldowns: dict[str, float] = {}
        self._lock = asyncio.Lock()
        self._cycle = itertools.cycle(range(max(len(self._keys), 1)))
        self._index = 0

    @property
    def size(self) -> int:
        return len(self._keys)

    def has_keys(self) -> bool:
        return bool(self._keys)

    async def acquire(self) -> str | None:
        if not self._keys:
            return None
        async with self._lock:
            now = time.monotonic()
            n = len(self._keys)
            for _ in range(n):
                idx = self._index % n
                self._index = (self._index + 1) % n
                key = self._keys[idx]
                until = self._cooldowns.get(key, 0.0)
                if until <= now:
                    return key
            # All cooling down — pick the one with earliest expiry
            best = min(self._keys, key=lambda k: self._cooldowns.get(k, 0.0))
            return best

    async def mark_failure(self, key: str | None, status_code: int | None = None) -> None:
        if not key:
            return
        # Cooldown on auth/quota style failures; also on explicit quota messages handled by caller
        if status_code is not None and status_code not in ROTATE_STATUS_CODES:
            # Still advance for 5xx? No — only rotate on ROTATE_STATUS_CODES or quota-class
            return
        async with self._lock:
            self._cooldowns[key] = time.monotonic() + self._cooldown_seconds
            logger.warning(
                "Ollama API key entered cooldown for %.0fs (status=%s)",
                self._cooldown_seconds,
                status_code,
            )

    async def mark_quota_failure(self, key: str | None) -> None:
        if not key:
            return
        async with self._lock:
            self._cooldowns[key] = time.monotonic() + self._cooldown_seconds
            logger.warning(
                "Ollama API key entered cooldown for %.0fs (quota-class failure)",
                self._cooldown_seconds,
            )


def _is_quota_error_body(body: str) -> bool:
    lower = body.lower()
    markers = ("quota", "rate limit", "rate_limit", "too many requests", "usage limit")
    return any(m in lower for m in markers)


class OllamaProvider:
    def __init__(
        self,
        *,
        base_url: str,
        api_keys: list[str] | None = None,
        connect_timeout: float = 5.0,
        read_timeout: float = 180.0,
        keep_alive: str = "10m",
        key_cooldown_seconds: float = 30.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.keep_alive = keep_alive
        self._key_pool = KeyPool(api_keys or [], cooldown_seconds=key_cooldown_seconds)
        self._owns_client = client is None
        timeout = httpx.Timeout(
            connect=connect_timeout,
            read=read_timeout,
            write=read_timeout,
            pool=connect_timeout,
        )
        self._client = client or httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout,
            headers={"Content-Type": "application/json"},
        )

    @property
    def key_pool(self) -> KeyPool:
        return self._key_pool

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    def _auth_headers(self, key: str | None) -> dict[str, str]:
        if key:
            return {"Authorization": f"Bearer {key}"}
        return {}

    async def chat(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        response_schema: dict[str, Any],
        options: dict[str, Any] | None = None,
        keep_alive: str | None = None,
        thinking: bool | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
            "format": response_schema,
            "options": options or {},
            "keep_alive": keep_alive or self.keep_alive,
        }
        if thinking is not None:
            payload["think"] = thinking

        last_error: Exception | None = None
        attempts = max(self._key_pool.size, 1)

        for attempt in range(attempts):
            key = await self._key_pool.acquire()
            headers = self._auth_headers(key)
            try:
                response = await self._client.post(
                    "/api/chat", json=payload, headers=headers
                )
            except httpx.TimeoutException as exc:
                raise TimeoutGatewayError(
                    "Ollama inference timed out",
                    code="ollama_timeout",
                    status_code=504,
                ) from exc
            except httpx.RequestError as exc:
                raise ServiceUnavailableError(
                    "Failed to connect to Ollama",
                    code="ollama_unavailable",
                ) from exc

            if response.status_code in ROTATE_STATUS_CODES:
                await self._key_pool.mark_failure(key, response.status_code)
                last_error = ServiceUnavailableError(
                    f"Ollama rejected request with status {response.status_code}",
                    code="ollama_unavailable",
                )
                if attempt + 1 < attempts:
                    continue
                raise last_error

            body_text = response.text
            if response.status_code >= 500:
                # Do not treat as key failure; surface as provider unavailable
                raise ServiceUnavailableError(
                    f"Ollama returned HTTP {response.status_code}",
                    code="ollama_unavailable",
                )

            if response.status_code == 404:
                raise ServiceUnavailableError(
                    "Ollama model or endpoint not found (HTTP 404)",
                    code="ollama_unavailable",
                )

            if response.status_code >= 400:
                if _is_quota_error_body(body_text):
                    await self._key_pool.mark_quota_failure(key)
                    last_error = ServiceUnavailableError(
                        "Ollama quota or rate limit exceeded",
                        code="ollama_unavailable",
                    )
                    if attempt + 1 < attempts:
                        continue
                    raise last_error
                raise ProviderError(
                    f"Ollama error HTTP {response.status_code}",
                    code="invalid_model_output",
                    status_code=502,
                )

            try:
                return response.json()
            except ValueError as exc:
                raise ProviderError(
                    "Ollama returned non-JSON response",
                    code="invalid_model_output",
                ) from exc

        if last_error:
            raise last_error
        raise ServiceUnavailableError("No Ollama API keys available")

    async def health(self) -> bool:
        """Best-effort connectivity check (tags or root)."""
        key = await self._key_pool.acquire()
        headers = self._auth_headers(key)
        try:
            # Prefer /api/tags; cloud may differ — also try GET /
            response = await self._client.get("/api/tags", headers=headers)
            if response.status_code < 500:
                return True
            response = await self._client.get("/", headers=headers)
            return response.status_code < 500
        except httpx.HTTPError:
            return False

    async def model_available(self, model: str) -> bool | None:
        """Return True/False if listable, None if cannot determine."""
        key = await self._key_pool.acquire()
        headers = self._auth_headers(key)
        try:
            response = await self._client.get("/api/tags", headers=headers)
            if response.status_code >= 400:
                return None
            data = response.json()
            models = data.get("models") or []
            names = {m.get("name") or m.get("model") for m in models if isinstance(m, dict)}
            return model in names or any(
                isinstance(n, str) and (n == model or n.startswith(model + ":"))
                for n in names
            )
        except httpx.HTTPError:
            return None
        except ValueError:
            return None
