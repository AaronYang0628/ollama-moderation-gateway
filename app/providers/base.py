"""Provider protocol / base types."""

from __future__ import annotations

from typing import Any, Protocol


class InferenceProvider(Protocol):
    async def chat(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        response_schema: dict[str, Any],
        options: dict[str, Any] | None = None,
        keep_alive: str | None = None,
    ) -> dict[str, Any]:
        ...

    async def health(self) -> bool:
        ...

    async def aclose(self) -> None:
        ...
