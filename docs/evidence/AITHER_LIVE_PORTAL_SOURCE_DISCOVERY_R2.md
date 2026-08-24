# Aither Live Portal Source Discovery R2 — Hermes Execution Evidence

- Task: `AITHER-LIVE-PORTAL-SOURCE-DISCOVERY-R2`
- Mode: `READ_ONLY_LIVE_PORTAL_SOURCE_DISCOVERY`
- Executor: `hermes`
- Branch: `aither-v2`
- Baseline SHA: `a29eb83833bfb004c18bfdb2c9f94aa2b719c033`
- HEAD (task-control): `085c0abca52aced399938541fe9ea35837fda72f`
- Start UTC: `2026-08-23T23:51:18Z`
- End UTC: `2026-08-23T23:58:20Z`
- Result: **PASS** — live serving chain proven end-to-end to a specific ConfigMap + repository artifact; no runtime/DB/credential/source mutation occurred; only this evidence file was written; no Git write performed by Hermes.

---

## 1. Preflight

| Item | Value |
|------|-------|
| hostname | `330133.fornex.cloud` (VPS2; `fb1.spb.ru` resolves to `130.17.1.90` = this host) |
| executor | root Hermes (repo owned by `codex`) |
| workdir | `/home/codex/aither-project` |
| `git rev-parse HEAD` | `085c0abca52aced399938541fe9ea35837fda72f` |
| `git rev-parse --abbrev-ref HEAD` | `aither-v2` |
| baseline ancestor of HEAD | YES |
| diff `baseline..HEAD` (name-only) | only `.agent/CURRENT_TASK.json` + `.agent/CURRENT_TASK.md` |

Git was invoked exclusively via `runuser -u codex -- git …` (no `safe.directory`, no Git metadata write by Hermes).

## 2. Live Portal serving chain (proven end-to-end)

```
user-facing URL  https://fb1.spb.ru:10443/   (also :443)
   │  (Server: nginx/1.31.3 — Docker container `aither-failover-nginx`,
   │   host-network nginx:alpine NGINX_VERSION=1.31.3, on VPS2 130.17.1.90)
   │  server_name fb1.spb.ru;  listen 10443 ssl;
   │  location / { proxy_pass http://10.129.13.78:30080; }
   ▼
K8s NodePort  10.129.13.78:30080
   ▼
Service `aither-portal`  (NodePort 80:30080/TCP, selector app=aither-portal)
   ns aither-inference, endpoint 10.244.1.74:80
   ▼
Pod `aither-portal-6c9dd7bcb9-9fzfd`  (10.244.1.74, node bootsmam-k8s-clnt01-n7-gpu)
   container `nginx`, image `nginx:stable-alpine`
   imageID docker.io/library/nginx@sha256:97d490c12ba55b4946b01546d1c3ed324e8d41ab1c9fcb2a616aa470620e5b46
   ▼
ConfigMap mounts (NO Secret mounts present on this pod):
   aither-portal-config  → /etc/nginx/conf.d     (key nginx.conf)
   aither-portal-config  → /usr/share/nginx/html (keys index.html, styles.css, app.js)
   aither-portal-docs    → /usr/share/nginx/html/docs (18 .md keys)
   ▼
served assets  index.html  +  app.js?v=final  +  styles.css
```

There is **no Kubernetes Ingress/Route** in `aither-inference`. The reverse-proxy layer in front of the NodePort is the VPS2 Docker container `aither-failover-nginx` (its `location /` proxies to `http://10.129.13.78:30080`).

## 3. Workload / service / pod / container / image identity

| Object | Identity |
|--------|----------|
| namespace | `aither-inference` |
| Service (user-facing) | `aither-portal`, NodePort `80:30080/TCP`, ClusterIP `10.100.145.83`, selector `app=aither-portal` |
| Endpoints | `10.244.1.74:80` |
| Pod | `aither-portal-6c9dd7bcb9-9fzfd`, node `bootsmam-k8s-clnt01-n7-gpu` |
| Container | `nginx` |
| Image | `nginx:stable-alpine` (imageID `docker.io/library/nginx@sha256:97d490c12ba55b4946b01546d1c3ed324e8d41ab1c9fcb2a616aa470620e5b46`) |
| Server header (NodePort) | `nginx/1.30.4` |
| Server header (fb1.spb.ru) | `nginx/1.31.3` (VPS2 failover-nginx) |

Secondary (NOT user-facing, ClusterIP only): Deployment `aither-portal-frontend` (image `10.129.13.78:5000/aither-portal-frontend:q25-d1-325781b`, ClusterIP `10.105.195.81:80`) mounts ConfigMap `aither-portal-frontend-config` at `/usr/share/nginx/html`. This service has no NodePort and is not the endpoint users reach.

## 4. Live served fingerprints (SHA-256)

Fetched unauthenticated (200 OK, no credentials/cookies/tokens used). Identical bytes from `https://fb1.spb.ru:10443/` and `http://10.129.13.78:30080/`.

| Asset | SHA-256 | bytes |
|-------|---------|-------|
| index.html | `ae9d12856976656094e6b480e71ffe958b16cde06b5e9bbdf7d77a7183c7f115` | 36116 |
| app.js?v=final | `3689164b5b21ac320c405b82d9694bce780d53bf4fca0a23d5d8addfc4ca945b` | 92923 |
| styles.css | `8471182055069271775f31cd65ca6ca75e85735744d7beb141ce628efc7f4626` | 16457 |

Non-sensitive headers recorded (index.html): `Content-Type: text/html; charset=utf-8`, `Content-Length: 36116`, `Last-Modified: Tue, 18 Aug 2026 12:44:40 GMT`, `ETag: "6a8453b8-8d14"`, `Accept-Ranges: bytes`. No Authorization/Cookie/Set-Cookie values were captured.

## 5. ConfigMap fingerprints (runtime)

| ConfigMap | key | SHA-256 | bytes | matches live? |
|-----------|-----|---------|-------|---------------|
| `aither-portal-config` | index.html | `ae9d12856976656094e6b480e71ffe958b16cde06b5e9bbdf7d77a7183c7f115` | 36116 | YES |
| `aither-portal-config` | app.js | `3689164b5b21ac320c405b82d9694bce780d53bf4fca0a23d5d8addfc4ca945b` | 92923 | YES |
| `aither-portal-config` | styles.css | `8471182055069271775f31cd65ca6ca75e85735744d7beb141ce628efc7f4626` | 16457 | YES |
| `aither-portal-config` | nginx.conf | `1aa8d01a533ff16fc2b7ed11226ea73c2484cdfc79008727963c074cc9982bce` | 3502 | (routing, not an asset) |
| `aither-portal-frontend-config` | app.js | `45b41805aa9029f1ec67fd110dad32f7cfc4a2fc73739d3b94d890b8703f9b1c` | 92996 | **NO** (not served) |
| `aither-portal-frontend-config` | index.html | `ae9d12856976656094e6b480e71ffe958b16cde06b5e9bbdf7d77a7183c7f115` | 36116 | same bytes, but not the served contour |
| `aither-portal-frontend-config` | styles.css | `8471182055069271775f31cd65ca6ca75e85735744d7beb141ce628efc7f4626` | 16457 | same bytes |
| `aither-portal-frontend-config` | nginx.conf | `1aa8d01a533ff16fc2b7ed11226ea73c2484cdfc79008727963c074cc9982bce` | 3502 | same bytes |

`aither-portal-frontend-config` app.js (45b41805…) is byte-identical to repository commit `39a8946143e7a38ceff9faabad024225acbf202e` ("feat(wui): markdown rendering + model descriptions + feedback file upload") — an older `/tokens`-based variant, not the live `/api-keys` variant.

## 6. Repository candidate fingerprints

| Repository artifact | SHA-256 | bytes | classification |
|---------------------|---------|-------|----------------|
| `aither-v2/services/portal-frontend/index.html` | `ae9d12856976656094e6b480e71ffe958b16cde06b5e9bbdf7d77a7183c7f115` | 36116 | **ACTIVE/CANONICAL** |
| `aither-v2/services/portal-frontend/app.js` | `3689164b5b21ac320c405b82d9694bce780d53bf4fca0a23d5d8addfc4ca945b` | 92923 | **ACTIVE/CANONICAL** |
| `aither-v2/services/portal-frontend/styles.css` | `8471182055069271775f31cd65ca6ca75e85735744d7beb141ce628efc7f4626` | 16457 | **ACTIVE/CANONICAL** |
| `aither-v2/services/portal-frontend/nginx.conf` | `1aa8d01a533ff16fc2b7ed11226ea73c2484cdfc79008727963c074cc9982bce` | 3502 | **ACTIVE/CANONICAL** |
| `portal/static/index.html` | `08e4544dbdb5829102bf60ecca19e73470549a6a5e45ba0d9e0cb662564005af` | 65211 | SUPERSEDED |
| `portal/dist/index.html` | `71b6f9cd223b92b37448878722918a6065b3cd1c80b4ebee3bf2e64700ebe151` | 78955 | SUPERSEDED |
| `deploy/portal-frontend-combined.html` | `16264fcca6c63d397f05971e374f422288fec223cb01277fe7d4e54a11d2c4b8` | 50240 | SUPERSEDED |
| `aither-v2/manifests/mvp-roadmap/07-portal/portal-mvp.yaml` | (embedded app.js uses `/tokens`; no `/api-keys`) | — | SUPERSEDED |
| `aither-v2/services/portal-frontend/k8s/portal-frontend.yaml` | (stage-15 inline single-file HTML) | — | SUPERSEDED |
| `aither-v2/tools/portal/index.html` | `390c3b43bc8e73e6c90c5742a74c031d1e0134f9af2153979d622cd832f616d2` | 8142 | UNREFERENCED/UNKNOWN |
| `aither-v2/tools/portal/app.js` | `a8a30f0048521d299314923c792cd67889d4330d67d8a955631c71531f354124` | 11382 | UNREFERENCED/UNKNOWN |

`aither-v2/services/portal-frontend/app.js` is byte-identical to repository commit `325781b44dd106137935f48842a76a1f279f35fa` ("fix: deduplicate Qwen2.5 scope labels in WUI") — the current HEAD-most commit touching that file.

## 7. Mapping table (runtime artifact → repository artifact)

| Runtime artifact | Repository artifact (byte-identical) |
|------------------|--------------------------------------|
| live `index.html` (fb1 + NodePort) | `aither-v2/services/portal-frontend/index.html` |
| live `app.js?v=final` (fb1 + NodePort) | `aither-v2/services/portal-frontend/app.js` |
| live `styles.css` (fb1 + NodePort) | `aither-v2/services/portal-frontend/styles.css` |
| ConfigMap `aither-portal-config` key `nginx.conf` | `aither-v2/services/portal-frontend/nginx.conf` |
| ConfigMap `aither-portal-config` (all 4 keys) | `aither-v2/services/portal-frontend/` source dir |

## 8. Model labels/IDs observed in the live served frontend (observation only)

The chat model selector is **hardcoded** in `index.html` (lines 242–244):

```
<select id="chat-model-select" ...>
  <option value="qwen2.5-32b-instruct">Qwen2.5-32B</option>
  <option value="qwen3-32b">Qwen3-32B</option>
```

Model IDs/labels referenced across the live `app.js`: `qwen2.5-32b-instruct`, `qwen3-32b` (plus display labels `Qwen2.5-32B`, `Qwen3-32B`), and usage-panel strings `qwen2.5-32b-instruct`, `qwen3-32b`.

## 9. Hardcoded vs API-populated model catalog

- **Chat model selector (`#chat-model-select`) is HARDCODED** — the two `<option>` elements are statically present in `index.html`; no JS call populates it.
- **Dashboard model list (`#dash-models`) is API-populated** — `app.js` line ~818 calls `api('/models')` and renders `res.data.data || res.data`.
- **Admin panel model list** is API-populated via `api('/admin/gateway/models')` (line ~1453).
- **Monitoring panel model list** is API-populated via `api('/monitoring/models')` (line ~1708).

No authentication was performed and no credentials were created during this task.

## 10. Commands used (sanitized)

- `runuser -u codex -- git rev-parse HEAD` / `git status --short` / `git log --oneline` / `git diff --name-only baseline..HEAD` / `git merge-base --is-ancestor`
- `kubectl -n aither-inference get deploy,svc,ingress,statefulset` and `get ingress` (→ none)
- `kubectl -n aither-inference get deploy aither-portal [-o jsonpath=…]` (image, volumes, volumeMounts)
- `kubectl -n aither-inference get deploy aither-portal-frontend [-o jsonpath=…]`
- `kubectl -n aither-inference get svc aither-portal [-o jsonpath=…]` + `get endpoints`
- `kubectl -n aither-inference get pods -l app=aither-portal [-o jsonpath=…]`
- `kubectl -n aither-inference get cm aither-portal-config -o json` / `get cm aither-portal-frontend-config -o json` / `get cm aither-portal-docs -o jsonpath`
- `curl -sk https://fb1.spb.ru:10443/ | http://10.129.13.78:30080/` (entry HTML, headers) — unauthenticated, non-sensitive
- `curl -sk "…/app.js?v=final"` and `"…/styles.css"` from both endpoints — unauthenticated
- `sha256sum` / `python3 hashlib` for deterministic fingerprints
- `docker ps` / `docker inspect aither-failover-nginx` / `docker exec aither-failover-nginx sh -c 'cat /etc/nginx/conf.d/*.conf'` (reverse-proxy target)
- `ss -tlnp`, `getent hosts fb1.spb.ru`

No `kubectl apply/create/patch/delete/rollout/exec(write)`, no Secret read, no credential use.

## 11. Required statements

- **RUNTIME_MUTATIONS: NONE**
- **SECRETS_EXPOSED: NO**

## 12. Conclusion

The canonical live Aither Portal frontend source is the repository directory:

**`aither-v2/services/portal-frontend/`** (`index.html`, `app.js`, `styles.css`, `nginx.conf`)

It is served to users through ConfigMap **`aither-portal-config`** (namespace `aither-inference`), mounted into the `aither-portal` nginx deployment (NodePort `:30080`), reached via `https://fb1.spb.ru:10443/` through the VPS2 `aither-failover-nginx` reverse proxy. All four source files are byte-identical (SHA-256) to both the live served assets and the ConfigMap keys. The Docker image (`nginx:stable-alpine`) contains no frontend content — the ConfigMap is the exclusive content source.

Superseded artifacts (`portal/static/index.html`, `portal/dist/index.html`, `deploy/portal-frontend-combined.html`, `manifests/mvp-roadmap/07-portal/portal-mvp.yaml`, `services/portal-frontend/k8s/portal-frontend.yaml`, and ConfigMap `aither-portal-frontend-config` app.js) do not match the live content. `aither-v2/tools/portal/*` has no runtime evidence tying it to the live Portal.
