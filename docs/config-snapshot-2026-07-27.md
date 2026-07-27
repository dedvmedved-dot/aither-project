# Aither Infrastructure Configuration Snapshot — 2026-07-27

> **WARNING:** This document is an INTERMEDIATE EMERGENCY CHECKPOINT.
> It is NOT accepted as-built documentation.
> Data requires external audit and subsequent reconciliation.

---

## 1. Purpose and Limitations

| Field | Value |
|---|---|
| Snapshot ID | `R7-R5-EMG-01-CHECKPOINT-01` |
| Emergency ID | `R7-R5-EMG-01-14B-N8-MIGRATION` |
| Captured (UTC) | 2026-07-27T12:36:10Z |
| Control T0 | `5cdb43b0147239eb3197b76183064b7054ed2098` |
| Accepted | NO |
| Reconciliation required | YES |

**Limitations:**
- Kubernetes Secret values excluded
- ConfigMap data content excluded (keys only)
- Runtime PIDs, IPs, tokens, passwords removed
- Environment variable values redacted
- Raw evidence stored locally in emergency journal only

---

## 2. Emergency ID and Checkpoint ID

```
EMERGENCY:  R7-R5-EMG-01-14B-N8-MIGRATION
CHECKPOINT: R7-R5-EMG-01-CHECKPOINT-01
```

Emergency was declared after discovering that vLLM 14B on N7 was running with `--cpu-offload-gb 10`, causing 50–100× slowdown and chat timeouts. Migration to N8 with TP=2 resolved the immediate crisis. Five hotfix commits were created. This checkpoint captures the state after all five commits but before any external audit.

---

## 3. Control T0

```
5cdb43b0147239eb3197b76183064b7054ed2098
```

This is the last commit present on both local and remote (`origin/aither-v2`). All five emergency commits are descendants of T0.

---

## 4. Local HEAD and Remote HEAD

| Reference | SHA |
|---|---|
| Local HEAD | `e5c795062d3b4eed5984c207cac04272f77bd589` |
| Remote HEAD (`origin/aither-v2`) | `5cdb43b0147239eb3197b76183064b7054ed2098` |
| Ancestor check | `e5c7950` is descendant of `5cdb43b` ✅ |
| Working tree | CLEAN |
| Branch | `aither-v2` |

---

## 5. Node Topology

| Node | Role | IP | OS | K8s | GPU |
|---|---|---|---|---|---|
| `bootsman-k8s-clnt01-n8-gpu` (40.51) | control-plane | 10.129.13.78 | Astra Linux 6.6.28 | v1.33.5 | 2× Quadro RTX 6000 (24 GB) |
| `bootsmam-k8s-clnt01-n7-gpu` (40.50) | worker | 10.129.13.77 | Astra Linux 6.6.28 | v1.33.5 | 2× Quadro RTX 6000 (24 GB) |

**Key labels:**
- N8: `aither.io/vllm14b-primary=true`
- N7: `aither.io/inference-primary=true`

---

## 6. Kubernetes Workloads

### aither-inference (production namespace)

| Deployment | Replicas | Node(s) | Status |
|---|---|---|---|
| `aither-bff` | 2 | N8 + N7 | Running (2/2) |
| `aither-portal` | 1 | N7 | Running |
| `aither-portal-backend` | 1 | N8 | Running |
| `aither-portal-frontend` | 1 | N7 | Running |
| `aither-identity` | 1 | N8 | Running |
| `aither-ai-platform` | 1 | N8 | Running |
| `aither-redis-rate-limit` | 1 | N8 | Running |
| `nginx-gateway-32b` | 2 | N8 + N7 | Running (2/2) |
| `vllm-14b-instruct` | 1 | **N8** | Running (TP=2, migrated) |
| `vllm-32b-gptq` | 1 | N7 | Running (TP=2) |

### aiops (analytics namespace)

| Component | Status |
|---|---|
| chromadb | Running (N8) |
| clickhouse | Running (N8) |
| flink-jobmanager | Running (N8) |
| flink-taskmanager | **CrashLoopBackOff** (N8, 1072 restarts) |
| kafka | Running (N8) |
| minio | Running (N8) |
| postgres | Running (N8) |

---

## 7. Model Placement

| Model | Node | Size | Quantization | TP | Status |
|---|---|---|---|---|---|
| Qwen2.5-14B-Instruct | **N8** | 28 GB | FP16 | 2 | ✅ Running (`vllm-14b-instruct`) |
| Qwen2.5-32B-GPTQ | N7 | 19 GB | GPTQ Int4 | 2 | ✅ Running (`vllm-32b-gptq`) |

**Idle models on disk (N8):**
- Qwen2.5-Coder-14B-Instruct (28 GB, FP16)
- Qwen2.5-Coder-14B (4.8 MB, base)
- saiga_llama3_8b (15 GB, FP16)
- lora-qwen14b-astra (209 MB, LoRA adapter)

---

## 8. GPU Allocation

### N8 (control-plane)

| GPU | UUID | Used (MB) | Workload |
|---|---|---|---|
| GPU 0 | `GPU-843d67db-…` | 20,185 / 23,040 | vllm-14b-instruct (TP=2, rank 0) |
| GPU 1 | `GPU-877a3026-…` | 20,185 / 23,040 | vllm-14b-instruct (TP=2, rank 1) |

### N7 (worker)

| GPU | UUID | Used (MB) | Workload |
|---|---|---|---|
| GPU 0 | `GPU-823a40a3-…` | 21,865 / 23,040 | vllm-32b-gptq (TP=2, rank 0) |
| GPU 1 | `GPU-73b74615-…` | 0 / 23,040 | **idle** (P8) |

> ⚠️ N7 GPU#1 is idle. This is anomalous for TP=2 on 32B. Investigation needed.

---

## 9. Internal and External Endpoints

| Service | Type | Cluster Port | Node Port | External |
|---|---|---|---|---|
| aither-portal | NodePort | 80/TCP | **30080** | ✅ `https://fb1.spb.ru:443` → 30080 |
| nginx-gateway-32b | NodePort | 8000/TCP | 30901 | Internal only |
| aither-ai-platform | NodePort | 8000/TCP | 30902 | Internal only |
| vllm-14b-instruct | ClusterIP | 8000 | — | Internal only |
| vllm-32b-gptq | ClusterIP | 8000 | — | Internal only |
| aither-bff | ClusterIP | 8000 | — | Internal only |
| aither-redis-rate-limit | ClusterIP | 6379 | — | Internal only |

---

## 10. BFF, Gateway and Nginx

### BFF (`aither-bff`, 2 replicas)

- Framework: FastAPI (Python)
- Version: `0.6.0-r7r7-c2-d18`
- Admin user_id fix applied (commit `55f45e1`)
- Connects to: PostgreSQL (K8s), Redis (K8s), Gateway (internal)
- Auth: JWT HS256, OAuth (GitHub/Google/Yandex), LDAP, dev-login

### Gateway (`nginx-gateway-32b`, 2 replicas)

- Python 3.12-slim running `gateway.py`
- Modules: JWT RS256, Rate Limiter (RPM/TPM), Billing (reserve→settle), Usage Collector, AI Security Gateway, Security Egress, SIEM CEF, Vault PKI, Wiki-Graph RAG, TTFT Metrics
- Catalog: `catalog.yaml` → routes 14B/32B requests to correct vLLM backend

### Nginx (Portal)

- Main portal nginx: `default_type text/plain; charset utf-8;`
- Proxies `/docs/` → portal-frontend
- SSE-compatible (proxy_buffering off)
- Portal-frontend nginx: serves 18 documentation markdown files

---

## 11. ConfigMap Index

| ConfigMap | Namespace | Keys | Purpose |
|---|---|---|---|
| `aither-bff-config` | aither-inference | config.yaml | BFF configuration |
| `aither-portal-config` | aither-inference | nginx.conf, styles.css, app.js, index.html | Portal nginx + static |
| `aither-portal-docs` | aither-inference | 18 markdown files | Portal documentation |
| `aither-portal-frontend-config` | aither-inference | nginx.conf, mime.types | Frontend nginx |
| `nginx-gateway-32b` | aither-inference | nginx.conf | Gateway nginx |

---

## 12. Secret References

| Secret | Keys | Used By |
|---|---|---|
| `aither-admin-credentials` | password_hash, username | aither-bff |
| `aither-bff-secrets` | JWT_SECRET, SESSION_SECRET, PGPASSWORD | aither-bff |
| `aither-portal-secrets` | oauth_client_secrets, invite_codes | aither-portal |

> Values excluded — see Kubernetes Secret store.

---

## 13. PVC and Model Storage

| PVC | Size | Status |
|---|---|---|
| `aither-ai-platform-data` | 1 Gi | Bound |
| `aither-identity-data` | 1 Gi | Bound |
| `aither-redis-data` | 1 Gi | Bound |

Models stored on hostPath:
- N8: `/data/models/` (8 directories, total ~118 GB)
- N7: `/data/models/` (2 active directories, 14B + 32B)

---

## 14. Redis Namespaces

| Instance | Namespace/Prefix | Purpose |
|---|---|---|
| `aither-redis-rate-limit` | `rl:{org_id}:rpm:{window}` | Rate limit RPM counters |
| `aither-redis-rate-limit` | `rl:{org_id}:tpm:{window}` | Rate limit TPM counters |
| `aither-redis-rate-limit` | `usage:{org_id}:{date}` | Daily token usage counters |
| `aither-redis-rate-limit` | `org_tier:{org_id}` | Tier cache (60s TTL) |
| `aither-redis-rate-limit` | `aither-auth:invite:` | Invite codes (7 keys, 30d TTL) |
| `aither-redis-rate-limit` | `ratelimit:{org_id}:{window}` | Legacy org-level rate limits |

> Values excluded — aggregated counts only in raw evidence.

---

## 15. Five Emergency Commits

| # | SHA | Date (UTC+3) | Message |
|---|---|---|---|
| 1 | `095afdc` | 2026-07-27T15:05:23 | `hotfix(portal): JS syntax, closeModal, feedback, AbortController, doc links, model card` |
| 2 | `55f45e1` | 2026-07-27T15:05:53 | `fix(bff): set req.state.user_id for admin sessions in _authenticate_request` |
| 3 | `efb563a` | 2026-07-27T15:06:37 | `fix(nginx): charset utf-8 + text/plain MIME for docs; proxy /docs/ via portal-frontend` |
| 4 | `dce645c` | 2026-07-27T15:07:00 | `docs(user-package): add 17_MODEL_USAGE_GUIDE — model architecture and usage guide` |
| 5 | `e5c7950` | 2026-07-27T15:08:12 | `infra(vllm-14b): migrate to N8 with tensor-parallel-size=2, remove CPU-offload` |

**Files changed (6 files, +231/-54):**
- `aither-v2/03-vllm-14b-deploy/manifests/vllm-deployment.yaml` — nodeSelector N8, TP=2, removed CPU-offload
- `aither-v2/deploy/portal/nginx.conf` — charset utf-8
- `aither-v2/docs/user-package/17_MODEL_USAGE_GUIDE.md` — new model usage guide
- `aither-v2/services/bff/app.py` — admin req.state.user_id
- `aither-v2/services/portal-frontend/nginx.conf` — charset utf-8
- `portal/static/index.html` — JS fixes + model card

---

## 16. Runtime-Only Changes

These changes are reflected in the running cluster but NOT captured in Git commits:

| # | Change | Reason |
|---|---|---|
| 1 | N8 node label: `aither.io/vllm14b-primary=true` | Required for vLLM 14B pod scheduling on N8 |
| 2 | BFF timeout: 600s → 300s (ConfigMap patch) | Restored after 14B speed improvement |
| 3 | Docs ConfigMap recovered (17 files) | Accidental overwrite during CM creation |

---

## 17. Git/Runtime Discrepancies

| Discrepancy | Detail |
|---|---|
| N8 node labels | Labels set via `kubectl label`, not in Git manifests |
| N7 GPU#1 idle | TP=2 on 32B should use both GPUs; only GPU#0 shows memory usage |
| flink-taskmanager | CrashLoopBackOff on N8 (1072 restarts, 5d5h age) |
| ConfigMap `aither-portal-docs` | 18 files present — recovered from repository after accidental overwrite |
| BFF replicas | 2 replicas in K8s, not reflected in repo deployment manifests |

---

## 18. Known Defects

| # | Defect | Severity | Status |
|---|---|---|---|
| 1 | N7 GPU#1 idle (32B TP=2 anomaly) | HIGH | Needs investigation |
| 2 | flink-taskmanager CrashLoopBackOff | MEDIUM | aiops namespace, not blocking |
| 3 | node-debugger pod Error state (default ns) | INFO | Stale debug pod |
| 4 | No GitHub push of emergency commits | HIGH | Addressed by this checkpoint |
| 5 | 32B model present on both N7 and N8 | LOW | Disk space concern |

---

## 19. Required Future Reconciliation

After emergency mode ends:
1. Reconcile K8s manifests in repository with actual cluster state
2. Investigate N7 GPU#1 idle state (32B TP=2)
3. Fix flink-taskmanager CrashLoopBackOff or remove aiops namespace
4. Clean up stale pods (test-curl*, tmp-curl*, node-debugger)
5. Add node labels to Git manifests
6. External audit of all 5 emergency commits
7. Determine if `aither.io/vllm14b-primary=true` on N8 is permanent

---

## 20. Snapshot Limitations

- This snapshot is **sanitized** — Secret values, ConfigMap data, runtime IDs excluded
- Raw evidence preserved in emergency journal at `/root/aither-emergency-journal/R7-R5-EMG-01-14B-N8-MIGRATION/artifacts/checkpoint-01-raw/`
- GPU process PIDs are runtime values — excluded from Git
- Redis keys counted but values excluded
- Not a substitute for a full cluster backup
- External audit required before accepting as authoritative

---

**End of snapshot. Reconciliation required.**
