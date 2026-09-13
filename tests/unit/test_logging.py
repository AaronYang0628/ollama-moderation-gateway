"""Logging redaction tests."""

from app.logging import redact_secrets


def test_redact_bearer() -> None:
    text = "Authorization: Bearer sk-secret-12345"
    assert "[REDACTED]" in redact_secrets(text)
    assert "sk-secret-12345" not in redact_secrets(text)


def test_redact_env_style() -> None:
    text = "OLLAMA_API_KEY=supersecret"
    assert "supersecret" not in redact_secrets(text)
