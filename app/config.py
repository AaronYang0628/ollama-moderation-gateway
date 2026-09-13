"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_model_aliases() -> dict[str, str]:
    return {
        "moderation-fast": os.getenv("MODEL_GPT_OSS_20B", "gpt-oss:20b"),
        "moderation-standard": os.getenv("MODEL_GEMMA4_31B", "gemma4:31b"),
        "moderation-accurate": os.getenv("MODEL_GPT_OSS_120B", "gpt-oss:120b"),
        "omni-moderation-latest": os.getenv("MODEL_GPT_OSS_20B", "gpt-oss:20b"),
        # Native names map to themselves
        "gpt-oss:20b": os.getenv("MODEL_GPT_OSS_20B", "gpt-oss:20b"),
        "gemma4:31b": os.getenv("MODEL_GEMMA4_31B", "gemma4:31b"),
        "gpt-oss:120b": os.getenv("MODEL_GPT_OSS_120B", "gpt-oss:120b"),
    }


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    app_env: str = Field(default="development", alias="APP_ENV")

    ollama_base_url: str = Field(default="https://ollama.com", alias="OLLAMA_BASE_URL")
    ollama_api_key: str | None = Field(default=None, alias="OLLAMA_API_KEY")
    ollama_api_keys: str | None = Field(default=None, alias="OLLAMA_API_KEYS")

    moderation_api_key: str | None = Field(default=None, alias="MODERATION_API_KEY")

    default_moderation_model: str = Field(
        default="moderation-fast", alias="DEFAULT_MODERATION_MODEL"
    )
    model_gpt_oss_20b: str = Field(default="gpt-oss:20b", alias="MODEL_GPT_OSS_20B")
    model_gemma4_31b: str = Field(default="gemma4:31b", alias="MODEL_GEMMA4_31B")
    model_gpt_oss_120b: str = Field(default="gpt-oss:120b", alias="MODEL_GPT_OSS_120B")

    ollama_connect_timeout_seconds: float = Field(
        default=5.0, alias="OLLAMA_CONNECT_TIMEOUT_SECONDS"
    )
    ollama_read_timeout_seconds: float = Field(
        default=180.0, alias="OLLAMA_READ_TIMEOUT_SECONDS"
    )
    request_timeout_seconds: float = Field(default=190.0, alias="REQUEST_TIMEOUT_SECONDS")
    max_input_chars: int = Field(default=16000, alias="MAX_INPUT_CHARS")
    max_batch_size: int = Field(default=32, alias="MAX_BATCH_SIZE")
    max_concurrency: int = Field(default=2, alias="MAX_CONCURRENCY")
    ollama_keep_alive: str = Field(default="10m", alias="OLLAMA_KEEP_ALIVE")
    key_cooldown_seconds: float = Field(default=30.0, alias="KEY_COOLDOWN_SECONDS")

    temperature: float = Field(default=0.2, alias="TEMPERATURE")
    top_p: float = Field(default=0.95, alias="TOP_P")
    top_k: int = Field(default=64, alias="TOP_K")
    thinking: bool = Field(default=False, alias="THINKING")

    uncertain_mode: str = Field(default="flag", alias="UNCERTAIN_MODE")
    policy_path: str = Field(default="configs/policy.yaml", alias="POLICY_PATH")
    policy_version: str = Field(default="v1", alias="POLICY_VERSION")
    prompt_version: str = Field(default="v1", alias="PROMPT_VERSION")

    allow_image_input: bool = Field(default=False, alias="ALLOW_IMAGE_INPUT")
    expose_backend_metadata: bool = Field(default=False, alias="EXPOSE_BACKEND_METADATA")
    expose_native_models: bool = Field(default=False, alias="EXPOSE_NATIVE_MODELS")
    enable_docs: bool = Field(default=True, alias="ENABLE_DOCS")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_raw_input: bool = Field(default=False, alias="LOG_RAW_INPUT")
    include_applied_input_types: bool = Field(
        default=True, alias="INCLUDE_APPLIED_INPUT_TYPES"
    )
    fallback_model: str | None = Field(default=None, alias="FALLBACK_MODEL")
    enable_fallback: bool = Field(default=False, alias="ENABLE_FALLBACK")
    cors_origins: str = Field(default="", alias="CORS_ORIGINS")

    @field_validator("uncertain_mode")
    @classmethod
    def _validate_uncertain_mode(cls, v: str) -> str:
        allowed = {"flag", "allow", "error"}
        if v not in allowed:
            raise ValueError(f"UNCERTAIN_MODE must be one of {allowed}")
        return v

    @field_validator("app_env")
    @classmethod
    def _normalize_env(cls, v: str) -> str:
        return v.lower().strip()

    @model_validator(mode="after")
    def _validate_production(self) -> Settings:
        if self.is_production:
            if not self.moderation_api_key:
                raise ValueError(
                    "MODERATION_API_KEY is required when APP_ENV=production"
                )
            if self.targets_ollama_cloud and not self.ollama_api_key_list:
                raise ValueError(
                    "At least one Ollama API key (OLLAMA_API_KEYS or OLLAMA_API_KEY) "
                    "is required when targeting ollama.com in production"
                )
        return self

    @property
    def is_production(self) -> bool:
        return self.app_env in {"production", "prod"}

    @property
    def is_test(self) -> bool:
        return self.app_env in {"test", "testing"}

    @property
    def targets_ollama_cloud(self) -> bool:
        base = self.ollama_base_url.rstrip("/").lower()
        return "ollama.com" in base

    @property
    def ollama_api_key_list(self) -> list[str]:
        keys: list[str] = []
        if self.ollama_api_keys:
            keys.extend(k.strip() for k in self.ollama_api_keys.split(",") if k.strip())
        if self.ollama_api_key and self.ollama_api_key.strip():
            if self.ollama_api_key.strip() not in keys:
                keys.append(self.ollama_api_key.strip())
        return keys

    @property
    def model_aliases(self) -> dict[str, str]:
        return {
            "moderation-fast": self.model_gpt_oss_20b,
            "moderation-standard": self.model_gemma4_31b,
            "moderation-accurate": self.model_gpt_oss_120b,
            "omni-moderation-latest": self.model_gpt_oss_20b,
            self.model_gpt_oss_20b: self.model_gpt_oss_20b,
            self.model_gemma4_31b: self.model_gemma4_31b,
            self.model_gpt_oss_120b: self.model_gpt_oss_120b,
        }

    @property
    def external_model_ids(self) -> list[str]:
        ids = [
            "moderation-fast",
            "moderation-standard",
            "moderation-accurate",
            "omni-moderation-latest",
        ]
        if self.expose_native_models:
            for native in {
                self.model_gpt_oss_20b,
                self.model_gemma4_31b,
                self.model_gpt_oss_120b,
            }:
                if native not in ids:
                    ids.append(native)
        return ids

    @property
    def cors_origin_list(self) -> list[str]:
        if not self.cors_origins.strip():
            return []
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def resolve_policy_path(self) -> Path:
        path = Path(self.policy_path)
        if path.is_absolute():
            return path
        # Resolve relative to project root (parent of app/)
        root = Path(__file__).resolve().parent.parent
        return root / path


@lru_cache
def get_settings() -> Settings:
    return Settings()


def clear_settings_cache() -> None:
    get_settings.cache_clear()
