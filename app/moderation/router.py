"""Model alias routing."""

from __future__ import annotations

from app.config import Settings
from app.errors import ModelNotFoundError


class ModelRouter:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.aliases = dict(settings.model_aliases)

    def resolve(self, model: str | None) -> tuple[str, str]:
        """Return (external_alias_or_name, effective_ollama_model)."""
        requested = model or self.settings.default_moderation_model
        if requested not in self.aliases:
            raise ModelNotFoundError(requested)
        return requested, self.aliases[requested]

    def list_external_ids(self) -> list[str]:
        return list(self.settings.external_model_ids)
