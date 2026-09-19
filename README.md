# Ollama Moderation Gateway

**OpenAI Moderations costs money and locks you in.** This gateway gives you the same `POST /v1/moderations` API, backed by free [Ollama](https://ollama.com) (Cloud or self-hosted) — multi-key, Docker/Helm ready, Apache-2.0.

> **Honest caveat:** scores come from general Ollama chat models, **not** OpenAI’s official classifiers. Useful for free / self-hosted audit — **not** a quality drop-in for `omni-moderation-latest`.

> **中文：** 免费的 Ollama AI 内容审核，接口兼容 OpenAI Moderations。质量**不等同于**官方审核模型。 → [中文站点](https://aaronyang0628.github.io/ollama-moderation-gateway/zh/) · [推广文案](docs/PROMOTE.md)

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-green.svg)](pyproject.toml)
[![PyPI](https://img.shields.io/pypi/v/ollama-moderation-gateway.svg)](https://pypi.org/project/ollama-moderation-gateway/)
[![Release](https://img.shields.io/github/v/release/AaronYang0628/ollama-moderation-gateway)](https://github.com/AaronYang0628/ollama-moderation-gateway/releases)

| | |
|---|---|
| **Repo** | [github.com/AaronYang0628/ollama-moderation-gateway](https://github.com/AaronYang0628/ollama-moderation-gateway) |
| **Site** | [EN](https://aaronyang0628.github.io/ollama-moderation-gateway/) · [中文](https://aaronyang0628.github.io/ollama-moderation-gateway/zh/) |
| **PyPI** | [`ollama-moderation-gateway`](https://pypi.org/project/ollama-moderation-gateway/) |
| **Helm** | [`charts/ollama-moderation-gateway/`](charts/ollama-moderation-gateway/) · [chart README](charts/ollama-moderation-gateway/README.md) |
| **Share** | [Community post templates](docs/PROMOTE.md) (v2ex / Reddit / HN · no fake stars) |

```mermaid
flowchart LR
  Client["Client / SDK / sub2api"] --> Gateway["Moderation Gateway"]
  Gateway --> Ollama["Ollama Cloud or self-host"]
```

---

## Quick start (~60s)

### Option A — pip (recommended)

```bash
pip install ollama-moderation-gateway

export APP_ENV=development
export MODERATION_API_KEY=local-moderation-key
# Ollama Cloud (optional for local smoke if you point at self-hosted):
# export OLLAMA_API_KEYS=your-cloud-key
# Self-hosted Ollama instead of ollama.com:
# export OLLAMA_BASE_URL=http://127.0.0.1:11434

ollama-moderation-gateway
# listens on http://0.0.0.0:8000
```

### Option B — Docker Compose

```bash
git clone https://github.com/AaronYang0628/ollama-moderation-gateway.git
cd ollama-moderation-gateway
cp .env.example .env
# Set MODERATION_API_KEY; set OLLAMA_API_KEYS if using Ollama Cloud
docker compose up --build
```

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
print(client.moderations.create(model="moderation-fast", input="Text to screen").results[0].flagged)
```

**Production** (`APP_ENV=production`) needs `MODERATION_API_KEY(S)` and, when using `ollama.com`, at least one `OLLAMA_API_KEYS` / `OLLAMA_API_KEY`.

<details>
<summary>Optional online demo (may sleep / cold-start — not the primary path)</summary>

A free-tier Render instance may exist at `https://ollama-moderation-gateway.onrender.com`. It often times out when spun down. Prefer local pip / Docker above.

</details>

---

## vs OpenAI Moderations

| | **This gateway** | **OpenAI Moderations** |
|---|---|---|
| **Cost** | Free Ollama (Cloud quota / your GPU) | Paid API |
| **API shape** | Compatible `POST /v1/moderations` | Official |
| **Quality** | General chat models — honest gap | Dedicated classifiers |
| **Hosting** | Self-host, Docker, Helm | SaaS only |
| **Keys** | Multi-key rotation + cooldown | Single vendor keys |

---

## What you get

- **Free Ollama-backed content audit** — cloud or your own host
- **OpenAI Moderations compatible** — point your client’s base URL here
- **Built for [sub2api](https://github.com/Wei-Shaw/sub2api)** — 风控中心 · 内容审计
- **Multi-key rotation** — round-robin; cooldown on 401 / 403 / 429 / quota
- **Lightweight** — Compose locally, Helm on Kubernetes for production
- **Safe defaults** — upstream failures return errors; never pretends content is clean

## Deploy

### Docker Compose

Copy `.env.example` → `.env`, set keys, `docker compose up --build`. Port **8000**. Never commit `.env`.

### Kubernetes with Helm (production)

Chart version **0.1.0** · image `ghcr.io/aaronyang0628/ollama-moderation-gateway:v0.1.0`.

Create the Secret out-of-band (`secrets.create: false` by default; then `secrets.existingSecret` is **required**). Ingress placeholder host: `moderation.example.com` — replace with **your** hostname; do not commit real prod domains.

```bash
kubectl create namespace moderation
kubectl -n moderation create secret generic ollama-moderation-gateway \
  --from-literal=OLLAMA_API_KEYS='key1,key2' \
  --from-literal=MODERATION_API_KEYS='gw-key1,gw-key2'

helm upgrade --install ollama-moderation-gateway ./charts/ollama-moderation-gateway \
  -n moderation --create-namespace \
  --set secrets.create=false \
  --set secrets.existingSecret=ollama-moderation-gateway \
  --set ingress.hosts[0].host=moderation.example.com \
  --set ingress.tls[0].hosts[0]=moderation.example.com \
  --set ingress.tls[0].secretName=moderation.example.com-tls
```

```bash
curl https://moderation.example.com/health
curl https://moderation.example.com/v1/moderations \
  -H 'Authorization: Bearer gw-key1' \
  -H 'Content-Type: application/json' \
  -d '{"model":"moderation-fast","input":"Text to screen"}'
```

More: [chart README](charts/ollama-moderation-gateway/README.md) · [Pages · Deploy](https://aaronyang0628.github.io/ollama-moderation-gateway/#deploy).

## Plug into sub2api

[sub2api](https://github.com/Wei-Shaw/sub2api) → 风控中心 · 内容审计 → point Moderations at this gateway.

| Setting | Value |
|---|---|
| **Base URL** | `http://localhost:8000` (local) or `https://moderation.example.com` (your deploy) — **no** trailing `/v1` |
| **Model** | `moderation-fast` (or `omni-moderation-latest` alias) |
| **API Key** | your gateway `MODERATION_API_KEY` — **not** an Ollama key |
| **timeout_ms** | `30000` (default `3000` is too short for cloud LLM) |

## Multi-key rotation

```dotenv
OLLAMA_API_KEYS=key1,key2,key3
# legacy single key still works:
OLLAMA_API_KEY=key1
```

Round-robin; bad keys cool down (`KEY_COOLDOWN_SECONDS`, default 30s). Gateway clients: `MODERATION_API_KEYS` the same way. **Never commit secrets.**

## Models

| You send | Ollama runs |
|---|---|
| `moderation-fast` | `gpt-oss:20b` |
| `moderation-standard` | `gemma4:31b` |
| `moderation-accurate` | `gpt-oss:120b` |
| `omni-moderation-latest` | `gpt-oss:20b` *(compat alias only)* |

Default backend: Ollama Cloud (`https://ollama.com`). Self-hosted: `OLLAMA_BASE_URL=http://127.0.0.1:11434`.

## API at a glance

| Method | Path | Notes |
|---|---|---|
| POST | `/v1/moderations` | OpenAI-style body & response |
| GET | `/v1/models` | Model list |
| GET | `/health` | Liveness |
| GET | `/readyz` | Ready when Ollama is reachable |

Env list: `.env.example`. Policy: `configs/policy.yaml`.

## Install from source / releases

```bash
pip install ollama-moderation-gateway
# or latest main:
pip install "git+https://github.com/AaronYang0628/ollama-moderation-gateway.git"
```

Wheels also on [GitHub Releases](https://github.com/AaronYang0628/ollama-moderation-gateway/releases). Dev clone: `pip install -e ".[dev]"`.

## Share / 推广

Ready-to-post templates (CN + EN) and ethical promo notes: **[docs/PROMOTE.md](docs/PROMOTE.md)**.

## License

Apache-2.0. Independent implementation — **no AGPL code copied**.
