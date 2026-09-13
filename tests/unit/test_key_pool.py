"""Key pool rotation unit tests."""

from __future__ import annotations

import pytest

from app.providers.ollama import KeyPool


@pytest.mark.asyncio
async def test_round_robin() -> None:
    pool = KeyPool(["a", "b", "c"], cooldown_seconds=60)
    keys = [await pool.acquire() for _ in range(6)]
    assert keys == ["a", "b", "c", "a", "b", "c"]


@pytest.mark.asyncio
async def test_cooldown_skips_key() -> None:
    pool = KeyPool(["a", "b"], cooldown_seconds=60)
    k1 = await pool.acquire()
    assert k1 == "a"
    await pool.mark_failure("a", 429)
    k2 = await pool.acquire()
    assert k2 == "b"
    k3 = await pool.acquire()
    # a still cooling — should prefer b
    assert k3 == "b"


@pytest.mark.asyncio
async def test_empty_pool() -> None:
    pool = KeyPool([])
    assert await pool.acquire() is None
