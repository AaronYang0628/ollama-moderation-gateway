# Ollama Moderation Gateway

**OpenAI-compatible Moderations API** — backed by [Ollama](https://ollama.com) Cloud or your own self-hosted models.

Drop-in for clients that speak `POST /v1/moderations`. Multi-key pool, FastAPI, Docker, **fail-closed** on provider errors. Apache-2.0.

> **中文摘要：** 基于 Ollama（云端或自托管）的 OpenAI 兼容内容审核网关。用通用对话模型做启发式风险评分，**不等同于** OpenAI `omni-moderation`。支持多 API Key 池、FastAPI、Docker；上游失败时不会伪造 `flagged=false`。演示站可能冷启动较慢。

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-green.svg)](pyproject.toml)
[![Demo](https://img.shields.io/badge/demo-onrender-orange.svg)](https://ollama-moderation-gateway.onrender.com)

| | |
|---|---|
| **Repo** | [github.com/AaronYang0628/ollama-moderation-gateway](https://github.com/AaronYang0628/ollama-moderation-gateway) |
| **Site** | [EN](https://aaronyang0628.github.io/ollama-moderation-gateway/) · [中文](https://aaronyang0628.github.io/ollama-moderation-gateway/zh/) |
| **Live demo** | [ollama-moderation-gateway.onrender.com](https://ollama-moderation-gateway.onrender.com) *(cold starts; use your own keys in production)* |

---

## Why this exists

Many stacks already call OpenAI’s Moderations endpoint. You may want the **same request/response shape** while routing inference through **Ollama** — Cloud SaaS by default, or a private host — with key rotation, policy thresholds, and Docker-friendly ops.

This gateway is that adapter: interface-compatible with common OpenAI Moderations clients, **independent implementation** (not a fork of AGPL `openedai-moderations`).

## Honest limits

This service scores text with **general-purpose chat models** (`gpt-oss:20b`, `gemma4:31b`, `gpt-oss:120b`). They are **not** dedicated safety classifiers.

- `category_scores` are **heuristic risk estimates** (0–1), not calibrated probabilities.
- Results are **not equivalent** to OpenAI `omni-moderation-latest` in quality, score scale, or behavior.
- Evaluate on your languages and risk profile before production (`scripts/evaluate.py`).

## Features

- `POST /v1/moderations` — string or string[] input, OpenAI-style response
- `GET /v1/models`, `GET /health`, `GET /readyz`
- Model aliases + native Ollama names
- Ollama native `POST /api/chat` with JSON Schema structured output
- Policy YAML thresholds + `uncertain_mode`: `flag` | `allow` | `error`
- **Multi API key pool** — round-robin; cooldown on `401` / `403` / `429` / quota failures
- Auth, batch concurrency limits, timeouts, log redaction
- Docker / Compose; pytest suite with mocked Ollama (no real keys required)
- **Fail-closed** — provider/parse failures return `502`/`503`/`504`; never fabricates `flagged=false`

## Quick start

```bash
git clone https://github.com/AaronYang0628/ollama-moderation-gateway.git
cd ollama-moderation-gateway

python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

cp .env.example .env
# Edit .env as needed. For local smoke without Cloud keys:
#   APP_ENV=development|test
#   optional: OLLAMA_BASE_URL → mock or self-hosted Ollama

pytest

export APP_ENV=development
export MODERATION_API_KEY=local-moderation-key
# Optional for Cloud:
# export OLLAMA_API_KEYS=your-cloud-key
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Production** (`APP_ENV=production`) requires:

1. `MODERATION_API_KEY`
2. At least one Ollama key when `OLLAMA_BASE_URL` targets `ollama.com`

### curl

```bash
curl http://localhost:8000/v1/moderations \
  -H 'Authorization: Bearer local-moderation-key' \
  -H 'Content-Type: application/json' \
  -d '{"model":"moderation-fast","input":"Text to screen"}'
```

### OpenAI Python SDK

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="local-moderation-key",
)

result = client.moderations.create(
    model="moderation-fast",
    input="Text to screen",
)
print(result.results[0].flagged)
```

### Docker

```bash
cp .env.example .env
# Set MODERATION_API_KEY, OLLAMA_API_KEYS (for Cloud), APP_ENV=production
docker compose up --build
```

## Backend: Ollama Cloud or self-hosted

| Setting | Default |
|---|---|
| `OLLAMA_BASE_URL` | `https://ollama.com` |
| Auth to Ollama | `Authorization: Bearer <key>` when keys are configured |
| Self-hosted | e.g. `OLLAMA_BASE_URL=http://127.0.0.1:11434` (typically no auth) |

Do **not** use `ollama.com/library/...` page URLs as the API base.

### Multi-key pool

```dotenv
OLLAMA_API_KEYS=key1,key2,key3
# legacy single key still supported:
OLLAMA_API_KEY=key1
```

Keys are round-robined. On HTTP `401` / `403` / `429` or quota-class errors, the failing key enters a short cooldown (`KEY_COOLDOWN_SECONDS`, default 30s) and the next key is tried. **Never commit secrets** — use `.env` (gitignored) or your secret manager.

### Model aliases

| Client `model` | Ollama model |
|---|---|
| `moderation-fast` | `gpt-oss:20b` |
| `moderation-standard` | `gemma4:31b` |
| `moderation-accurate` | `gpt-oss:120b` |
| `omni-moderation-latest` | `gpt-oss:20b` *(compatibility alias only)* |

Native names are also accepted. Mapping is configurable via env (`MODEL_*`). No local GPU and **no automatic model pull** on gateway startup (cloud-first).

**Self-hosted notes:** From Compose on Linux, host Ollama is often `http://host.docker.internal:11434` — not `127.0.0.1` inside the container. Pull models yourself (`ollama pull gpt-oss:20b`); large models need substantial RAM/VRAM beyond file size.

## API surface

| Method | Path | Auth | Notes |
|---|---|---|---|
| POST | `/v1/moderations` | Bearer when key set | OpenAI-style body/response |
| GET | `/v1/models` | Bearer when key set | External aliases |
| GET | `/health` | No | Liveness |
| GET | `/readyz` | No | Ollama reachability + default model |
| GET | `/docs` | — | Toggle with `ENABLE_DOCS` |

Errors:

```json
{"error": {"message": "...", "type": "...", "param": "...", "code": "..."}}
```

Configuration priority: process env → `.env` (pydantic-settings) → code defaults. Full list in `.env.example`. Policy thresholds: `configs/policy.yaml` (`POLICY_PATH`). Env `UNCERTAIN_MODE` overrides YAML `uncertain_mode`.


## Integrations

### sub2api（风控中心 · 内容审计）

[sub2api](https://github.com/Wei-Shaw/sub2api) can point its content-audit Moderations backend at this gateway.

Verified tips (also on the [EN](https://aaronyang0628.github.io/ollama-moderation-gateway/#integrations) / [中文](https://aaronyang0628.github.io/ollama-moderation-gateway/zh/#integrations) Pages):

- **Base URL:** `https://ollama-moderation-gateway.onrender.com` — **no** trailing `/v1` (sub2api appends `/v1/moderations`; `/v1` → `/v1/v1/...` → `{"detail":"Not Found"}`)
- **Model:** `moderation-fast` (or `omni-moderation-latest` alias)
- **API Key:** gateway `MODERATION_API_KEY` (placeholder: `your-gateway-api-key`), **not** Ollama keys; public demo may need your own deploy key
- **timeout_ms:** `30000` (default `3000` is too short for cloud LLM + Render cold start)
- Scores are **heuristic**, not OpenAI-equivalent

### 中文文档

完整产品页：[中文 GitHub Pages](https://aaronyang0628.github.io/ollama-moderation-gateway/zh/) · 英文：[EN](https://aaronyang0628.github.io/ollama-moderation-gateway/)

## Evaluation

```bash
python scripts/evaluate.py \
  --base-url http://localhost:8000/v1 \
  --api-key local-moderation-key \
  --dataset evals/samples/sample_eval.jsonl \
  --model moderation-fast \
  --out evals/reports/latest_report.json
```

See `evals/samples/` and `evals/reports/REPORT_TEMPLATE.md`.

## Security

- Gateway API key compared with constant-time `secrets.compare_digest`
- Logs redact Bearer tokens / key-like strings; raw input off by default (`LOG_RAW_INPUT`)
- User text wrapped in `<content>...</content>` — must not override system policy
- CORS off unless `CORS_ORIGINS` is set
- Do not expose the raw Ollama port to the public internet

## Project layout

```text
app/                 FastAPI app, providers, moderation pipeline
configs/policy.yaml  Thresholds & category definitions
docs/                GitHub Pages landing site
tests/               Unit + mock integration (incl. key rotation)
scripts/evaluate.py  Offline eval harness
Dockerfile / compose Cloud-first deployment
```

## Known limitations (MVP)

- No Prometheus metrics exporter yet (structured logs only)
- No ensemble / multi-model voting
- No multimodal / image moderation
- Fallback model stubs exist but are disabled by default (`ENABLE_FALLBACK=false`)
- Cloud `/api/tags` readiness is best-effort
- Real-model smoke tests are optional and need your own keys/hardware

## License

Apache-2.0. Interface design is informed by the public OpenAI Moderations API shape and community gateways; **no AGPL code was copied**.
