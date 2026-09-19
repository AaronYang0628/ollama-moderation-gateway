# Share / 推广 — community post templates

Honest promotion only. Goal: real stars from people who find the project useful.

**Primary CTA everywhere:** `pip install ollama-moderation-gateway` or Docker Compose + curl — **not** a sleeping Render demo.

Repo: https://github.com/AaronYang0628/ollama-moderation-gateway  
PyPI: https://pypi.org/project/ollama-moderation-gateway/  
Site: https://aaronyang0628.github.io/ollama-moderation-gateway/

---

## What NOT to do

- Do **not** buy stars, bots, or “growth services”
- Do **not** run mutual-star rings or “star for star” threads
- Do **not** spam the same post across every channel in one hour
- Do **not** claim quality equals OpenAI `omni-moderation-latest`
- Do **not** paste real prod hostnames, cluster IPs, or API keys
- Do **not** open fake PRs on awesome-lists just to farm links — read each list’s contribution guide first

---

## 中文 · v2ex

**标题：** 开源一个兼容 OpenAI Moderations 的免费审核网关（Ollama 后端）

**正文：**

做内容审计时不想为 OpenAI Moderations 单独付一笔，又不想改客户端协议，于是做了这个小网关：

- 对外仍是 `POST /v1/moderations`
- 背后走 Ollama（Cloud 或自建），多 Key 轮换
- `pip install ollama-moderation-gateway` 或 Docker / Helm 一把上
- 可对接 sub2api「风控中心 · 内容审计」

实话：质量**不等于** OpenAI 官方审核模型，适合免费 / 自托管场景，上线前请用自己的流量测。

GitHub：https://github.com/AaronYang0628/ollama-moderation-gateway  
文档：https://aaronyang0628.github.io/ollama-moderation-gateway/zh/

欢迎拍砖、提 issue。

---

## 中文 · 掘金

**标题：** 用 Ollama 跑一套 OpenAI 兼容的 Moderations API（开源网关）

**导语：** OpenAI Moderations 贵 + 锁厂商；本地/云端 Ollama 便宜但协议不统一。这个网关把两者接上。

**正文要点：**

1. 问题：已有工具（SDK、sub2api）只认 `/v1/moderations`
2. 方案：轻量 FastAPI 网关 → Ollama；多 Key + Docker/Helm
3. 60 秒：`pip install ollama-moderation-gateway` → 设 `MODERATION_API_KEY` → curl
4. 诚实对比表：成本 / 兼容 / 质量
5. 链接 GitHub + 中文站；欢迎 Star / Issue

---

## 中文 · 即刻

免费 OpenAI 兼容内容审核网关开源了：背后是 Ollama，接口仍是 `/v1/moderations`，可接 sub2api。  
`pip install ollama-moderation-gateway`  
质量 ≠ OpenAI 官方，适合自托管省钱。  
https://github.com/AaronYang0628/ollama-moderation-gateway

---

## English · Reddit r/LocalLLaMA

**Title:** Free OpenAI-compatible Moderations API backed by Ollama (multi-key, Docker/Helm)

**Body:**

I wanted Moderations without paying OpenAI or rewriting clients that already call `POST /v1/moderations`.

**ollama-moderation-gateway** sits in front of Ollama Cloud or a local Ollama:

```bash
pip install ollama-moderation-gateway
export APP_ENV=development MODERATION_API_KEY=local-moderation-key
# optional: OLLAMA_API_KEYS=... or OLLAMA_BASE_URL=http://127.0.0.1:11434
ollama-moderation-gateway
```

Then curl `POST /v1/moderations` as usual. Also works with tools like sub2api.

**Caveat:** scores come from general chat models, not OpenAI’s official moderation classifiers. Great for free/self-hosted audit — measure on your own traffic.

Repo: https://github.com/AaronYang0628/ollama-moderation-gateway

Happy to take feedback / PRs.

---

## English · Reddit r/selfhosted

**Title:** Self-host an OpenAI Moderations–compatible API with Ollama

Same story as LocalLLaMA, lean harder on Docker Compose + Helm:

- Compose for a single box
- Helm chart for k8s (`moderation.example.com` placeholder — use your domain)
- Multi client keys + Ollama key rotation

Link README Quick start. Mention quality honesty once. No fake “always-on demo” claims.

---

## Hacker News — Show HN

**Title:** Show HN: Free OpenAI-compatible moderations API backed by Ollama

**Body (2 paragraphs):**

OpenAI Moderations is convenient but paid and vendor-locked. Many tools already speak `POST /v1/moderations`. This small gateway keeps that API and runs scoring on Ollama (Cloud or self-hosted), with multi-key rotation, Docker Compose, and a Helm chart.

Install with `pip install ollama-moderation-gateway` or Compose, set `MODERATION_API_KEY`, and curl. Quality is not the same as OpenAI’s official classifiers — it’s for free/self-hosted content audit. Feedback welcome: https://github.com/AaronYang0628/ollama-moderation-gateway

---

## Awesome-list style — who to ping (do not spam)

Search first; follow each repo’s CONTRIBUTING / PR template; open **one** thoughtful PR with a short blurb.

| List | Search |
|---|---|
| awesome-ollama / Ollama tools | https://github.com/search?q=awesome+ollama&type=repositories |
| awesome-selfhosted | https://github.com/awesome-selfhosted/awesome-selfhosted (category: Automation / Misc / Security — read guidelines) |
| awesome-llm / AI gateways | https://github.com/search?q=awesome+llm+gateway&type=repositories |
| Helm / CNCF related lists | only if chart is production-ready and list accepts apps |

Suggested one-liner for lists:

> OpenAI-compatible Moderations API gateway backed by Ollama (Cloud/self-host), multi-key, Docker/Helm — https://github.com/AaronYang0628/ollama-moderation-gateway

---

## Suggested first post (pick one)

**Best first channel for this project:** **v2ex** (CN audience + sub2api / 风控 overlap) **or** **r/LocalLLaMA** (EN, Ollama-native crowd).

Ship one solid post, engage replies for a day, then cross-post a shorter version elsewhere.
