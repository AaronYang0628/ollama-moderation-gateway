"""OpenAI-compatible request/response schemas (Pydantic v2)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

DEFAULT_CATEGORIES = [
    "sexual",
    "sexual/minors",
    "harassment",
    "harassment/threatening",
    "hate",
    "hate/threatening",
    "illicit",
    "illicit/violent",
    "self-harm",
    "self-harm/intent",
    "self-harm/instructions",
    "violence",
    "violence/graphic",
]


class ModerationRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    input: str | list[str]
    model: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _reject_multimodal(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        raw_input = data.get("input")
        if isinstance(raw_input, list):
            for item in raw_input:
                if isinstance(item, dict):
                    raise ValueError(
                        "Multimodal / image inputs are not supported; only text is allowed"
                    )
                if item is not None and not isinstance(item, str):
                    raise ValueError("Each input element must be a string")
        elif raw_input is not None and not isinstance(raw_input, str):
            if isinstance(raw_input, dict):
                raise ValueError(
                    "Multimodal / image inputs are not supported; only text is allowed"
                )
            raise ValueError("input must be a string or array of strings")
        return data

    @field_validator("input")
    @classmethod
    def _validate_input(cls, v: str | list[str]) -> str | list[str]:
        if isinstance(v, str):
            if not v.strip():
                raise ValueError("input must not be empty or whitespace-only")
            return v
        if isinstance(v, list):
            if len(v) == 0:
                raise ValueError("input array must not be empty")
            for i, item in enumerate(v):
                if not isinstance(item, str):
                    raise ValueError(f"input[{i}] must be a string")
                if not item.strip():
                    raise ValueError(f"input[{i}] must not be empty or whitespace-only")
            return v
        raise ValueError("input must be a string or array of strings")


class Categories(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sexual: bool = False
    sexual_minors: bool = Field(default=False, alias="sexual/minors")
    harassment: bool = False
    harassment_threatening: bool = Field(default=False, alias="harassment/threatening")
    hate: bool = False
    hate_threatening: bool = Field(default=False, alias="hate/threatening")
    illicit: bool = False
    illicit_violent: bool = Field(default=False, alias="illicit/violent")
    self_harm: bool = Field(default=False, alias="self-harm")
    self_harm_intent: bool = Field(default=False, alias="self-harm/intent")
    self_harm_instructions: bool = Field(default=False, alias="self-harm/instructions")
    violence: bool = False
    violence_graphic: bool = Field(default=False, alias="violence/graphic")

    def to_openai_dict(self) -> dict[str, bool]:
        return {
            "sexual": self.sexual,
            "sexual/minors": self.sexual_minors,
            "harassment": self.harassment,
            "harassment/threatening": self.harassment_threatening,
            "hate": self.hate,
            "hate/threatening": self.hate_threatening,
            "illicit": self.illicit,
            "illicit/violent": self.illicit_violent,
            "self-harm": self.self_harm,
            "self-harm/intent": self.self_harm_intent,
            "self-harm/instructions": self.self_harm_instructions,
            "violence": self.violence,
            "violence/graphic": self.violence_graphic,
        }


class CategoryScores(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sexual: float = 0.0
    sexual_minors: float = Field(default=0.0, alias="sexual/minors")
    harassment: float = 0.0
    harassment_threatening: float = Field(default=0.0, alias="harassment/threatening")
    hate: float = 0.0
    hate_threatening: float = Field(default=0.0, alias="hate/threatening")
    illicit: float = 0.0
    illicit_violent: float = Field(default=0.0, alias="illicit/violent")
    self_harm: float = Field(default=0.0, alias="self-harm")
    self_harm_intent: float = Field(default=0.0, alias="self-harm/intent")
    self_harm_instructions: float = Field(default=0.0, alias="self-harm/instructions")
    violence: float = 0.0
    violence_graphic: float = Field(default=0.0, alias="violence/graphic")

    def to_openai_dict(self) -> dict[str, float]:
        return {
            "sexual": self.sexual,
            "sexual/minors": self.sexual_minors,
            "harassment": self.harassment,
            "harassment/threatening": self.harassment_threatening,
            "hate": self.hate,
            "hate/threatening": self.hate_threatening,
            "illicit": self.illicit,
            "illicit/violent": self.illicit_violent,
            "self-harm": self.self_harm,
            "self-harm/intent": self.self_harm_intent,
            "self-harm/instructions": self.self_harm_instructions,
            "violence": self.violence,
            "violence/graphic": self.violence_graphic,
        }


class ModerationResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    flagged: bool
    categories: dict[str, bool]
    category_scores: dict[str, float]
    category_applied_input_types: dict[str, list[str]] | None = None


class ModerationResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    model: str
    results: list[ModerationResult]
    metadata: dict[str, Any] | None = None


class ModelInfo(BaseModel):
    id: str
    object: str = "model"
    created: int = 0
    owned_by: str = "ollama-moderation-gateway"


class ModelListResponse(BaseModel):
    object: str = "list"
    data: list[ModelInfo]


class HealthResponse(BaseModel):
    status: str = "ok"


class ReadyResponse(BaseModel):
    status: str
    detail: str | None = None
    code: str | None = None
