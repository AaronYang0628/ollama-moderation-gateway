# ollama-moderation-gateway Helm chart

Kubernetes install for the Ollama Moderation Gateway. Chart version **0.1.0**, appVersion **0.1.0**.

This is the **production** path. Docker Compose is fine on a single host; an optional Render demo may sleep / cold-start — prefer Compose or this Helm chart for anything real.

Product docs: [README · Deploy](../../README.md#deploy) · [Pages · Deploy](https://aaronyang0628.github.io/ollama-moderation-gateway/#deploy).

## Install

Prefer creating the Secret **out-of-band**, then install from the local chart path. Default `secrets.create` is `false`; when that is false, `secrets.existingSecret` is **required** or the chart fails.

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

Requires Kubernetes `>= 1.25`.

### Image

Default: `ghcr.io/aaronyang0628/ollama-moderation-gateway:v0.1.0`.

Images are published to GHCR on `main` and version tags by [`.github/workflows/container.yml`](../../.github/workflows/container.yml). If the package is private, set `imagePullSecrets`.

### Cluster proxy defaults

`HTTP_PROXY` / `HTTPS_PROXY` default to empty. Set them only if your cluster needs egress proxy (prefer a private values overlay; do not commit real proxy endpoints):

```bash
--set env.HTTP_PROXY= \
--set env.HTTPS_PROXY= \
--set env.NO_PROXY=
```

…or a values file.

### Smoke

Example production host (chart ingress default):

```bash
curl https://moderation.example.com/health

curl https://moderation.example.com/v1/moderations \
  -H 'Authorization: Bearer gw-key1' \
  -H 'Content-Type: application/json' \
  -d '{"model":"moderation-fast","input":"Text to screen"}'
```

Service is ClusterIP port **8000**. Liveness is `GET /health`; readiness is `GET /readyz`.

## Values

| Key | Default | Notes |
|---|---|---|
| `replicaCount` | `1` | |
| `image.repository` | `ghcr.io/aaronyang0628/ollama-moderation-gateway` | GHCR |
| `image.tag` | `v0.1.0` | Ignored if `image.digest` is set |
| `image.digest` | `""` | Optional immutable digest (`repo@sha256:…`) |
| `image.pullPolicy` | `IfNotPresent` | |
| `imagePullSecrets` | `[]` | Needed for private GHCR |
| `service.type` | `ClusterIP` | |
| `service.port` | `8000` | |
| `env.APP_ENV` | `production` | |
| `env.APP_HOST` | `0.0.0.0` | |
| `env.APP_PORT` | `"8000"` | |
| `env.OLLAMA_BASE_URL` | `https://ollama.com` | Self-hosted: your Ollama URL |
| `env.DEFAULT_MODERATION_MODEL` | `moderation-fast` | |
| `env.ENABLE_DOCS` | `"false"` | |
| `env.HTTP_PROXY` / `HTTPS_PROXY` / `NO_PROXY` | empty / localhost defaults | Set only if your cluster needs egress proxy; keep real values out of git |
| `env.LOG_LEVEL` | `INFO` | |
| `env.LOG_RAW_INPUT` | `"false"` | Keep false in production |
| `extraEnv` / `extraEnvFrom` | `[]` | Extra container env |
| `secrets.create` | `false` | `true` only for local / non-prod |
| `secrets.existingSecret` | `ollama-moderation-gateway` | Required when `create` is false |
| `secrets.stringData.*` | empty | Used only if `secrets.create: true` |
| `ingress.enabled` | `true` | |
| `ingress.className` | `nginx` | |
| `ingress.hosts[0].host` | `moderation.example.com` | **Placeholder** — set your real host via private values / `--set` |
| `ingress.tls[0].secretName` | `moderation.example.com-tls` | cert-manager / your TLS secret |
| `ingress.annotations` | cert-manager `lets-encrypt`; nginx body 5m; connect 30s; read/send 300s | |
| `resources.requests` | cpu `100m`, memory `256Mi` | |
| `resources.limits` | cpu `1`, memory `1Gi` | |
| `livenessProbe.httpGet.path` | `/health` | `initialDelaySeconds: 10`, `periodSeconds: 30` |
| `readinessProbe.httpGet.path` | `/readyz` | `initialDelaySeconds: 15`, `periodSeconds: 15` |

Non-sensitive env goes to a ConfigMap (`env.*`). API keys stay in a Secret.

Secret keys (from `secrets.stringData` / the existing Secret):

- `OLLAMA_API_KEYS`
- `OLLAMA_API_KEY`
- `MODERATION_API_KEYS`
- `MODERATION_API_KEY`

## Security notes

- **Do not commit secrets.** Create the Secret with `kubectl` (or your secret manager) and point `secrets.existingSecret` at it.
- `secrets.create: true` writes keys from `values.yaml` into a chart-managed Secret. That is **only for local / non-prod**.
- Pods run as non-root (`runAsUser` / `runAsGroup` `10001`), read-only root filesystem, and drop all capabilities. `seccompProfile` is `RuntimeDefault`. Privilege escalation is disabled.
- Production env defaults: `APP_ENV=production`, `ENABLE_DOCS=false`, `LOG_RAW_INPUT=false`.
- Never put real `OLLAMA_API_KEY(S)` or `MODERATION_API_KEY(S)` in Git, chart values committed to the repo, or CI logs.
