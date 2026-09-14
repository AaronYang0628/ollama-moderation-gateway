# Ollama Moderation Gateway

**Free AI content moderation** powered by [Ollama](https://ollama.com) — with an OpenAI Moderations–compatible API.

Plug it into anything that already calls `POST /v1/moderations` (OpenAI SDK, [sub2api](https://github.com/Wei-Shaw/sub2api), and similar tools). Lightweight, multi-key rotation, Docker- and Helm-ready. Apache-2.0.

> **中文：** 免费的 Ollama AI 内容审核 / 审计服务。接口兼容 OpenAI Moderations，可直接对接 sub2api 等工具。轻量、多 Key 轮换、即插即用。质量**不等同于** OpenAI 官方审核模型。 → [中文站点](https://aaronyang0628.github.io/ollama-moderation-gateway/zh/)

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-green.svg)](pyproject.toml)
[![Demo](https://img.shields.io/badge/demo-onrender-orange.svg)](https://ollama-moderation-gateway.onrender.com)
[![Release](https://img.shields.io/github/v/release/AaronYang0628/ollama-moderation-gateway)](https://github.com/AaronYang0628/ollama-moderation-gateway/releases)

| | |
|---|---|
| **Repo** | [github.com/AaronYang0628/ollama-moderation-gateway](https://github.com/AaronYang0628/ollama-moderation-gateway) |
| **Site** | [EN](https://aaronyang0628.github.io/ollama-moderation-gateway/) · [中文](https://aaronyang0628.github.io/ollama-moderation-gateway/zh/) |
| **Live demo** | [ollama-moderation-gateway.onrender.com](https://ollama-moderation-gateway.onrender.com) *(free tier may cold-start; demo only)* |
| **Helm chart** | [`charts/ollama-moderation-gateway/`](charts/ollama-moderation-gateway/) (v0.1.0) · [chart README](charts/ollama-moderation-gateway/README.md) · [Pages · Deploy](https://aaronyang0628.github.io/ollama-moderation-gateway/#deploy) |

> **Honest note:** Scores come from general Ollama chat models, not OpenAI’s official moderation classifiers. Useful for free / self-hosted content audit — **not** a drop-in quality match for `omni-moderation-latest`.

---

## What you get

- **Free Ollama-backed content audit** — cloud or your own host, no OpenAI Moderations bill
- **OpenAI Moderations compatible** — same request/response shape; point your client’s base URL here
- **Built for sub2api** — drop into 风控中心 · 内容审计 as the Moderations backend
- **Multi-key rotation** — round-robin across Ollama keys; auto-cooldown on 401 / 403 / 429 / quota
- **Lightweight & easy** — one small gateway; Docker Compose locally, Helm on Kubernetes for production
- **Safe defaults** — upstream failures return errors; never pretends content is clean

## Quick start

```bash
git clone https://github.com/AaronYang0628/ollama-moderation-gateway.git
cd ollama-moderation-gateway

python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

cp .env.example .env
# Edit .env — for local smoke without Cloud keys:
#   APP_ENV=development
#   optional: OLLAMA_BASE_URL → self-hosted Ollama

export APP_ENV=development
export MODERATION_API_KEY=local-moderation-key
# Optional for Ollama Cloud:
# export OLLAMA_API_KEYS=your-cloud-key
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Production** (`APP_ENV=production`) needs:

1. `MODERATION_API_KEY` (or `MODERATION_API_KEYS`)
2. At least one Ollama key when using `ollama.com`

### Try it

```bash
curl http://localhost:8000/v1/moderations \
  -H 'Authorization: Bearer local-moderation-key' \
  -H 'Content-Type: application/json' \
  -d '{"model":"moderation-fast","input":"Text to screen"}'
```

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

Kubernetes / production: [Deploy](#deploy). Chart notes: [`charts/ollama-moderation-gateway/README.md`](charts/ollama-moderation-gateway/README.md).

## Deploy

Local smoke is [Quick start](#quick-start). For anything you actually run: Compose on a single host, **Helm on Kubernetes** for production.

Chart: [`charts/ollama-moderation-gateway/`](charts/ollama-moderation-gateway/) · [chart README](charts/ollama-moderation-gateway/README.md) · product site [EN · Deploy](https://aaronyang0628.github.io/ollama-moderation-gateway/#deploy) · [中文 · 部署](https://aaronyang0628.github.io/ollama-moderation-gateway/zh/#deploy).

### Docker Compose

Same as above: copy `.env.example` → `.env`, set keys, `docker compose up --build`. Listens on port **8000**. Never commit `.env`.

### Kubernetes with Helm (production)

This is the production path. Chart version **0.1.0**, appVersion **0.1.0**.

**Create the Secret out-of-band**, then `helm upgrade --install` from the local chart path. The chart does **not** create a Secret by default (`secrets.create: false`). When that is false, `secrets.existingSecret` is **required** or the install fails.

- **Image:** `ghcr.io/aaronyang0628/ollama-moderation-gateway:v0.1.0` (GHCR; published on `main` and version tags by [`.github/workflows/container.yml`](.github/workflows/container.yml)). Private GHCR packages need `imagePullSecrets`.
- **Service:** ClusterIP port **8000**. Liveness `GET /health`, readiness `GET /readyz`.
- **Ingress defaults:** enabled, class `nginx`, host `moderation.llm.72602.space`, TLS secret `moderation.llm.72602.space-tls`, cert-manager cluster-issuer `lets-encrypt`, nginx read/send timeouts 300s.
- **Proxy note:** chart `env` defaults include `HTTP_PROXY` / `HTTPS_PROXY` / `NO_PROXY` pointing at `192.168.0.25:17890`. Those are **example cluster values**. On any other cluster, clear or override them (`--set env.HTTP_PROXY=` / `HTTPS_PROXY=` / `NO_PROXY=`, or a values file).

```bash
kubectl create namespace moderation
kubectl -n moderation create secret generic ollama-moderation-gateway \
  --from-literal=OLLAMA_API_KEYS='key1,key2' \
  --from-literal=MODERATION_API_KEYS='gw-key1,gw-key2'

helm upgrade --install ollama-moderation-gateway ./charts/ollama-moderation-gateway \
  -n moderation --create-namespace \
  --set secrets.create=false \
  --set secrets.existingSecret=ollama-moderation-gateway \
  --set ingress.hosts[0].host=moderation.llm.72602.space \
  --set ingress.tls[0].hosts[0]=moderation.llm.72602.space \
  --set ingress.tls[0].secretName=moderation.llm.72602.space-tls
```

Secret keys the chart expects: `OLLAMA_API_KEYS`, `OLLAMA_API_KEY`, `MODERATION_API_KEYS`, `MODERATION_API_KEY`. `secrets.create: true` is **only for local / non-prod** — do not put real keys in Git or in committed values files.

Override the ingress host (and TLS secret) if you are not using `moderation.llm.72602.space`.

**Smoke** (example production host):

```bash
curl https://moderation.llm.72602.space/health

curl https://moderation.llm.72602.space/v1/moderations \
  -H 'Authorization: Bearer gw-key1' \
  -H 'Content-Type: application/json' \
  -d '{"model":"moderation-fast","input":"Text to screen"}'
```

### Render demo

The [onrender.com demo](https://ollama-moderation-gateway.onrender.com) is **demo-only**. Free tier may cold-start; do not treat it as production.

## Plug into sub2api

[sub2api](https://github.com/Wei-Shaw/sub2api) → 风控中心 · 内容审计 → point Moderations at this gateway.

| Setting | Value |
|---|---|
| **Base URL** | `https://ollama-moderation-gateway.onrender.com` — **no** trailing `/v1` (sub2api already appends `/v1/moderations`) |
| **Model** | `moderation-fast` (or `omni-moderation-latest` alias) |
| **API Key** | your gateway `MODERATION_API_KEY` — **not** an Ollama key |
| **timeout_ms** | `30000` (default `3000` is too short for cloud LLM + cold start) |

More detail: [EN site](https://aaronyang0628.github.io/ollama-moderation-gateway/#integrations) · [中文站点](https://aaronyang0628.github.io/ollama-moderation-gateway/zh/#integrations)

## Multi-key rotation

```dotenv
OLLAMA_API_KEYS=key1,key2,key3
# legacy single key still works:
OLLAMA_API_KEY=key1
```

Keys rotate round-robin. On `401` / `403` / `429` or quota errors, the bad key cools down (`KEY_COOLDOWN_SECONDS`, default 30s) and the next one takes over. **Never commit secrets** — use `.env` (gitignored) or your secret manager.

Gateway clients can use `MODERATION_API_KEYS` the same way (comma-separated).

## Models

| You send | Ollama runs |
|---|---|
| `moderation-fast` | `gpt-oss:20b` |
| `moderation-standard` | `gemma4:31b` |
| `moderation-accurate` | `gpt-oss:120b` |
| `omni-moderation-latest` | `gpt-oss:20b` *(compat alias only)* |

Native Ollama names also work. Default backend is Ollama Cloud (`https://ollama.com`); set `OLLAMA_BASE_URL` for self-hosted (e.g. `http://127.0.0.1:11434`).

## API at a glance

| Method | Path | Notes |
|---|---|---|
| POST | `/v1/moderations` | OpenAI-style body & response |
| GET | `/v1/models` | Model list |
| GET | `/health` | Liveness |
| GET | `/readyz` | Ready when Ollama is reachable |

Full env list: `.env.example`. Policy thresholds: `configs/policy.yaml`.


## Install / Release

Once published to PyPI:

```bash
pip install ollama-moderation-gateway
ollama-moderation-gateway
```

Until then (or for the latest main):

```bash
pip install "git+https://github.com/AaronYang0628/ollama-moderation-gateway.git"
# or a specific release tag:
pip install "git+https://github.com/AaronYang0628/ollama-moderation-gateway.git@v0.1.0"
```

Binary wheels and source archives are attached to [GitHub Releases](https://github.com/AaronYang0628/ollama-moderation-gateway/releases).

PyPI Trusted Publishing is optional: configure a pending publisher on [pypi.org](https://pypi.org) for package `ollama-moderation-gateway`, repo `AaronYang0628/ollama-moderation-gateway`, workflow `release.yml`, environment `pypi`. Until that is set, tag releases still upload assets to GitHub Releases only.

## License

Apache-2.0. Independent implementation — **no AGPL code copied**.
