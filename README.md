# Ollama Moderation Gateway

OpenAI-compatible **Moderations API** gateway backed by [Ollama](https://ollama.com) (Cloud SaaS by default, or self-hosted).

**License:** Apache-2.0  
**Independent implementation** — interface-compatible with common OpenAI Moderations clients; **not** a fork of AGPL `openedai-moderations`.

## Important disclaimer (non-equivalence)

This service routes moderation through **general-purpose chat models** (`gpt-oss:20b`, `gemma4:31b`, `gpt-oss:120b`). They are **not** dedicated safety classifiers.

- `category_scores` are **heuristic risk estimates** (0–1), **not** calibrated probabilities.
- Results are **not equivalent** to OpenAI `omni-moderation-latest` in quality, score scale, or behavior.
- Always evaluate on your languages and risk profile before production use (`scripts/evaluate.py`).

## Features (MVP)

- `POST /v1/moderations` — string or string[] input, OpenAI-style response
- `GET /v1/models`, `GET /health`, `GET /readyz`
- Model aliases + native Ollama names
- Ollama native `POST /api/chat` with JSON Schema structured output
- Policy YAML thresholds + `uncertain_mode`: `flag` | `allow` | `error`
- **Multi API key pool** with round-robin and cooldown on 401/403/429/quota failures
- Auth, batch concurrency limits, timeouts, log redaction
- Docker / Compose, pytest suite (mocked Ollama — no real keys required)

## Default inference backend: Ollama Cloud

| Setting | Default |
|---|---|
| `OLLAMA_BASE_URL` | `https://ollama.com` |
| Auth to Ollama | `Authorization: Bearer <key>` when keys configured |
| Self-hosted | Set `OLLAMA_BASE_URL=http://127.0.0.1:11434` (no auth) |

> Do **not** use `ollama.com/library/...` page URLs as the API base.

### Multi-key configuration

```dotenv
OLLAMA_API_KEYS=key1,key2,key3
# legacy single key still supported:
OLLAMA_API_KEY=key1
```

Keys are round-robined. On HTTP `401` / `403` / `429` or quota-class errors, the failing key enters a short cooldown (`KEY_COOLDOWN_SECONDS`, default 30s) and the next key is tried. **Never commit secrets** — use `.env` (gitignored) or your secret manager.

## Model aliases

| Client `model` | Ollama model |
|---|---|
| `moderation-fast` | `gpt-oss:20b` |
| `moderation-standard` | `gemma4:31b` |
| `moderation-accurate` | `gpt-oss:120b` |
| `omni-moderation-latest` | `gpt-oss:20b` (compatibility alias only) |

Native names (`gpt-oss:20b`, `gemma4:31b`, `gpt-oss:120b`) are also accepted. Mapping is configurable via env (`MODEL_*`).

No local GPU and **no automatic model pull** on gateway startup (cloud-first).

## Quick start (local)

```bash
cd /workspace/ollama-moderation-gateway   # or your checkout path
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

cp .env.example .env
# For local smoke without Cloud keys, use APP_ENV=development|test
# and optionally point OLLAMA_BASE_URL at a mock / self-hosted Ollama.

# Run tests (mocked; no real Ollama keys required)
pytest

# Start server (dev)
export APP_ENV=development
export MODERATION_API_KEY=local-moderation-key
# Optional for Cloud:
# export OLLAMA_API_KEYS=your-cloud-key
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Production mode (`APP_ENV=production`) **requires**:

1. `MODERATION_API_KEY`
2. At least one Ollama key when `OLLAMA_BASE_URL` targets `ollama.com`

## curl example

```bash
curl http://localhost:8000/v1/moderations \
  -H 'Authorization: Bearer local-moderation-key' \
  -H 'Content-Type: application/json' \
  -d '{"model":"moderation-fast","input":"待审核文本"}'
```

## OpenAI Python SDK

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="local-moderation-key",
)

result = client.moderations.create(
    model="moderation-fast",
    input="待审核文本",
)
print(result.results[0].flagged)
```

## Docker

```bash
cp .env.example .env
# Edit .env: MODERATION_API_KEY, OLLAMA_API_KEYS (for Cloud), APP_ENV=production

docker compose up --build
```

### Self-hosted Ollama notes

- From Compose on Linux, host Ollama is often `http://host.docker.internal:11434` or the docker bridge IP — **not** `127.0.0.1` inside the container.
- Same Compose network: set `OLLAMA_BASE_URL=http://ollama:11434` and uncomment the optional `ollama` service in `docker-compose.yml`.
- Self-hosted typically needs **no** `OLLAMA_API_KEY(S)`.

### Model preparation (self-hosted only)

```bash
ollama list
ollama pull gpt-oss:20b   # explicit; gateway never auto-pulls
```

Large models (especially 120B) need substantial RAM/VRAM beyond file size (KV cache, context, concurrency).

## Configuration priority

1. Process environment variables  
2. `.env` file (via pydantic-settings)  
3. Code defaults  

See `.env.example` for the full list. Policy thresholds live in `configs/policy.yaml` (override path with `POLICY_PATH`). Env `UNCERTAIN_MODE` overrides the YAML `uncertain_mode`.

## API surface

| Method | Path | Auth | Notes |
|---|---|---|---|
| POST | `/v1/moderations` | Bearer when key set | OpenAI-style body/response |
| GET | `/v1/models` | Bearer when key set | External aliases |
| GET | `/health` | No | Liveness |
| GET | `/readyz` | No | Ollama reachability + default model |
| GET | `/docs` | — | Toggle with `ENABLE_DOCS` |

Errors use:

```json
{"error": {"message": "...", "type": "...", "param": "...", "code": "..."}}
```

On provider/parse failures the gateway returns **502/503/504** — it **never** fabricates `flagged=false`.

## Evaluation

```bash
python scripts/evaluate.py \
  --base-url http://localhost:8000/v1 \
  --api-key local-moderation-key \
  --dataset evals/samples/sample_eval.jsonl \
  --model moderation-fast \
  --out evals/reports/latest_report.json
```

Sample format and report template: `evals/samples/`, `evals/reports/REPORT_TEMPLATE.md`.

## Security notes

- Gateway API key compared with constant-time `secrets.compare_digest`
- Logs redact Bearer tokens / key-like strings; raw input off by default (`LOG_RAW_INPUT`)
- User text is wrapped in `<content>...</content>` and must not override the system policy
- CORS off unless `CORS_ORIGINS` is set
- Do not expose the raw Ollama port to the public internet

## Project layout

```text
app/                 FastAPI app, providers, moderation pipeline
configs/policy.yaml  Thresholds & category definitions
tests/               Unit + mock integration (incl. key rotation)
scripts/evaluate.py  Offline eval harness
Dockerfile / compose Cloud-first deployment
```

## Known limitations / PRD gaps (MVP)

- No Prometheus metrics exporter yet (structured logs only)
- No ensemble / multi-model voting
- No multimodal / image moderation
- Fallback model config exists as env stubs but is disabled by default (`ENABLE_FALLBACK=false`)
- Cloud `/api/tags` readiness is best-effort; some SaaS layouts may not list models the same way as self-hosted
- Real-model smoke tests are optional and require your own keys/hardware

## License & attribution

Apache-2.0. Interface design is informed by the public OpenAI Moderations API shape and the existence of community gateways; **no AGPL code was copied**.
