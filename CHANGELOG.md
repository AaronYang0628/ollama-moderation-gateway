# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-09-13

### Added

- **MVP gateway**: OpenAI-compatible `POST /v1/moderations` (plus `/v1/models`, `/health`, `/readyz`) backed by Ollama Cloud or self-hosted Ollama.
- **Multi Ollama API keys**: comma-separated `OLLAMA_API_KEYS` with round-robin rotation and cooldown on 401 / 403 / 429 / quota errors.
- **Multi gateway client keys**: `MODERATION_API_KEYS` / `MODERATION_API_KEY` for authenticating callers.
- **Docker**: `Dockerfile` and `docker-compose.yml` for one-command deploys.
- **sub2api notes**: documented how to point 风控中心 · 内容审计 at this gateway (base URL without trailing `/v1`, model aliases, timeout).
- **GitHub Pages**: product site (EN + 中文) at `aaronyang0628.github.io/ollama-moderation-gateway`.
- **Packaging**: installable Python package with CLI entrypoint `ollama-moderation-gateway`, CI, and GitHub Releases.

[0.1.0]: https://github.com/AaronYang0628/ollama-moderation-gateway/releases/tag/v0.1.0
