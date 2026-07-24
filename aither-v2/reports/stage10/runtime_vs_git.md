# Stage 10 — Runtime vs Git Comparison

## Task 3 — Mapping Git ↔ Runtime for Each Component

### Methodology
- **Git baseline:** Commit `75931e6` (session-close) plus committed RC2 changes (`65c8b33`, `519970f`)
- **Current HEAD:** `519970f` — these 2 commits ARE in Git
- **Uncommitted changes** noted separately with `⚠️ LOCAL ONLY`
- **No runtime inspection was performed** — this is a Git-to-Git mapping per task constraints

---

## Comparison Table

| # | Component | In Git | In Git Since | Notes |
|---|-----------|--------|-------------|-------|
| 1 | **AI Platform Deployment** | ✅ `aither-v2/services/ai-platform/k8s/ai-platform.yaml` | `75931e6` | Image: `stage18a-82fe433`. PVC, liveness/readiness probes defined. |
| 2 | **AI Platform Code** | ✅ `aither-v2/services/ai-platform/app/main.py` | `75931e6` | ⚠️ **LOCAL ONLY:** SQLite fix (timeout=10, busy_timeout, retry_on_lock) — not committed. HEAD version has no fix. |
| 3 | **AI Platform Dockerfile** | ✅ `aither-v2/services/ai-platform/Dockerfile` | `75931e6` | Standard python:3.11-slim. No changes. |
| 4 | **Portal Backend Deployment** | ✅ `aither-v2/services/portal-backend/k8s/portal-backend.yaml` | `75931e6` | Image: `stage18a-82fe433`. Correct env vars. |
| 5 | **Portal Frontend ConfigMap** | ✅ `aither-v2/services/portal-frontend/k8s/portal-frontend.yaml` | `75931e6` | Embeds `index.html` + `nginx.conf`. |
| 6 | **Portal Frontend nginx.conf** | ✅ `aither-v2/services/portal-frontend/nginx.conf` (source) | `75931e6` | ⚠️ **LOCAL ONLY:** Security headers added (CSP, X-Frame, etc.) — not committed. |
| 7 | **Identity Deployment** | ✅ `aither-v2/services/identity/k8s/identity.yaml` | `75931e6` | Image: `stage18a-82fe433`. PVC mounted. |
| 8 | **Gateway (nginx-gateway-32b)** | ✅ `aither-v2/03-vllm-14b-deploy/manifests/nginx-gateway-32b.yaml` | `75931e6` | Contains ConfigMap + Deployment + Service in single file. Image: `nginx:alpine` (sha256-pinned). |
| 9 | **Gateway nginx config** | ✅ `aither-v2/03-vllm-14b-deploy/manifests/nginx-gateway-32b.conf` | `75931e6` | ⚠️ **Not used by current ConfigMap.** The ConfigMap in YAML has its own inline config with rate limiting (`limit_req_zone`, 30r/m, burst=5). The `.conf` file is a separate artifact. |
| 10 | **Check T-486 gateway (Python)** | ✅ `manifests/gateway.yaml`, `gateway/admin.py` etc. | `75931e6` | Python-based gateway code exists in Git but **not deployed** (replaced by nginx-gateway-32b). |
| 11 | **Check T-486 gateway (deploy)** | ✅ `manifests/gateway-deploy.yaml` | `75931e6` | Also not used — nginx gateway is the active runtime component. |
| 12 | **vLLM Deployment** | ✅ `aither-v2/03-vllm-14b-deploy/manifests/vllm-deployment.yaml` | `75931e6` | qwen-32b-gptq. PVC, service, network policy defined. |
| 13 | **vLLM Service** | ✅ `aither-v2/03-vllm-14b-deploy/manifests/vllm-service.yaml` | `75931e6` | ClusterIP service, port 8000. |
| 14 | **Secrets** | ⚠️ **Partial** | `75931e6` | Example files exist (`identity-secret.example.yaml`). Actual secrets (VLLM_API_KEY, identity secrets) are NOT in Git — managed via `kubectl create secret`. |
| 15 | **PVCs** | ✅ `aither-v2/services/ai-platform/k8s/ai-platform.yaml` + identity and model PVCs | `75931e6` | AI Platform (1Gi), Identity (1Gi), model PVC (separate manifest). |
| 16 | **ConfigMap: nginx-gateway-32b** | ✅ Embedded in `nginx-gateway-32b.yaml` | `75931e6` | Contains: rate limiting (30r/m, burst=5), completion proxy, health/models endpoints. |
| 17 | **ConfigMap: aither-portal-frontend** | ✅ Embedded in `portal-frontend.yaml` | `75931e6` | Full index.html + nginx.conf with proxy to portal-backend. |
| 18 | **ConfigMap: gateway-code** | ✅ `manifests/gateway.yaml` | `75931e6` | Redundant — Python gateway not deployed. |

---

## Git vs Local Working Tree Mismatches

| Component | Git (HEAD) | Local Working Tree | Impact |
|-----------|-----------|-------------------|--------|
| `main.py` (AI Platform) | No SQLite fix | SQLite fix present | Fix was **deployed to runtime** but not in Git |
| `nginx.conf` (Portal Frontend) | No security headers | Security headers added | Headers were **not deployed** — only in local tree |
| `v1.0.md` (Release Notes) | "Production v1.0" | "Internal Pilot RC2R" | Documentation corrected locally |
| `reports/rc2r/` | 0 files (not in Git) | 8 report files | All RC2R evidence/reports are local only |
| `evidence/rc2r/` | 0 files (not in Git) | ~55 evidence files | Evidence collected but not committed |
| `scripts/rc2r/` | 0 files (not in Git) | 4 test scripts | Test scripts not committed |
| `docs/rc2r-corrections.md` | Not in Git | Exists locally | Correction document not committed |

---

## Key Observations

1. **All manifests are in Git** — every Deployment, Service, ConfigMap, PVC, and Secret template exists in the committed repository at `75931e6`+2 commits.

2. **Runtime may differ from Git** — notably:
   - AI Platform pod runs image `rc2r-sqlite-fix` (pushed and deployed during RC2R), while Git still references `stage18a-82fe433`
   - Gateway ConfigMap may have been updated in runtime (rate limiting applied) — the inline config in Git already has rate limiting, so this likely matches

3. **Code changes are NOT in Git** — the SQLite fix (`main.py`) and security headers (`nginx.conf`) are only in the local working tree. These were deployed to runtime during RC2R but never committed.

4. **Reports and evidence are NOT in Git** — all RC2R outputs exist only locally.

5. **No runtime inspection was performed** for this report — only Git content was examined, as required by the task constraints.
