# Aither Architect Report — 2026-07-27

> **Emergency Checkpoint:** R7-R5-EMG-01-CHECKPOINT-01
> **Prepared for:** External audit by ChatGPT (Architect)
> **Prepared by:** Hermes Agent (DeepSeek)

---

## Executive Summary

During R7-R5 corrective implementation C2, a critical performance defect was discovered: vLLM 14B on N7 was running with `--cpu-offload-gb 10`, causing 50–100× slowdown. This triggered Emergency R7-R5-EMG-01-14B-N8-MIGRATION. Five hotfix commits were created to resolve the crisis and fix related portal/BFF issues. The emergency is ongoing. This report captures the checkpoint state for external audit before continuing emergency operations or transitioning to post-emergency reconciliation.

---

## Current Status

| Field | Value |
|---|---|
| **U1.3-OPS-R7-R5** | IN PROGRESS |
| **R7-R5-C3** | PAUSED |
| **EMERGENCY MODE** | ACTIVE |
| **POST-EMERGENCY RECONCILIATION** | NOT STARTED |
| **SECURITY INCIDENT** | OPEN |
| **DIRECTION 02** | NOT AUTHORIZED |
| **LIMITED USER HANDOVER** | PROHIBITED |
| **CONTROLLED BETA** | BLOCKED |
| **PUSH TO GITHUB** | YES — fast-forward checkpoint committed |

---

## Repository Status

| Parameter | Value |
|---|---|
| Repository | `dedvmedved-dot/aither-project` |
| Branch | `aither-v2` |
| Local HEAD | `e5c795062d3b4eed5984c207cac04272f77bd589` |
| Remote HEAD | `5cdb43b0147239eb3197b76183064b7054ed2098` |
| Working tree | CLEAN |
| Ancestor | Local HEAD is descendant of remote HEAD ✅ |
| Pending push | 5 commits + 1 snapshot commit |

---

## Five Emergency Commits

| # | SHA (short) | Description |
|---|---|---|
| 1 | `095afdc` | **hotfix(portal):** JS syntax fix (duplicate `const pages`), window.closeModal, feedback form POST, AbortController 300s timeout, doc links fix, 9th model card |
| 2 | `55f45e1` | **fix(bff):** Admin sessions now set `req.state.user_id`, `user_role`, `username` in `_authenticate_request` — fixes "User identity required" on API key creation |
| 3 | `efb563a` | **fix(nginx):** Charset utf-8 + text/plain MIME for docs on both portal and portal-frontend nginx; proxy `/docs/` via portal-frontend |
| 4 | `dce645c` | **docs(user-package):** New `17_MODEL_USAGE_GUIDE.md` — architecture, 14B vs 32B differences, endpoints, usage patterns |
| 5 | `e5c7950` | **infra(vllm-14b):** Migrate 14B from N7 to N8 with tensor-parallel-size=2, remove `--cpu-offload-gb 10`. Node label `aither.io/vllm14b-primary=true` on N8. |

**Total delta:** 6 files changed, +231/-54 lines (all append-only per emergency protocol).

---

## 20 Declared Emergency Changes

### Git-committed (5)

See commits above.

### Runtime-only (3)

| # | Change | Detail |
|---|---|---|
| R1 | N8 node label | `kubectl label node bootsman-k8s-clnt01-n8-gpu aither.io/vllm14b-primary=true --overwrite` |
| R2 | BFF timeout restore | ConfigMap `aither-bff-config` patched: timeout 600s → 300s (after 14B speed restored) |
| R3 | Docs ConfigMap recovery | 17 original files recovered after accidental overwrite during `aither-docs-files` creation |

### Kubernetes resource changes (from commits 1-5)

- `vllm-14b-instruct` Deployment: nodeSelector → N8, GPU 1→2, TP 1→2, removed `--cpu-offload-gb 10`, removed `--swap-space 4`, `--gpu-memory-utilization 0.85→0.90`, `--max-model-len 2048→4096`
- `aither-portal` ConfigMap: nginx.conf updated (charset utf-8, /docs/ location block), index.html updated (JS fixes)
- `aither-portal-frontend` ConfigMap: nginx.conf updated (charset utf-8)
- `aither-bff` ConfigMap: updated with patched `_authenticate_request`
- `aither-docs-files` ConfigMap: recovered 17 files + 1 new (18 total)

### Portal/BFF hotfixes applied (from commits 1-4)

| Fix | Issue | Result |
|---|---|---|
| JS SyntaxError (`const pages` duplicate) | Admin login broken | Fixed |
| `window.closeModal` not in global scope | Close button in API key modal broken | Fixed |
| Feedback form was no-op | Empty handler, only cleared field | Now saves + POSTs |
| No client-side timeout | Chat hung on slow model | AbortController 300s added |
| Doc links with `/docs/user-package/` prefix | 404 on documentation links | Fixed to `/docs/` |
| Admin `req.state.user_id` missing | "User identity required" on token creation | Fixed |
| `Content-Type: text/markdown` without charset | Cyrillic garbled in docs | `text/plain; charset=utf-8` |
| No `/docs/` location block in portal nginx | 404 on all documentation | Added proxy_pass to portal-frontend |
| Missing model usage documentation | Users confused about 14B vs 32B | Added `17_MODEL_USAGE_GUIDE.md` + 9th card |

---

## Current Infrastructure Health

### GPU and Models

| Component | Node | Status | Detail |
|---|---|---|---|
| vLLM 14B | N8 | ✅ Running | TP=2, ~0.1 sec/token, 20.2 GB VRAM per GPU |
| vLLM 32B | N7 | ✅ Running | TP=2, **⚠️ GPU#1 idle** (0 MB used) |

### Core Services

| Service | Status | Detail |
|---|---|---|
| aither-bff | ✅ Running | 2/2 replicas (N8 + N7) |
| aither-portal | ✅ Running | NodePort 30080 |
| aither-portal-frontend | ✅ Running | Documentation serving correctly |
| nginx-gateway-32b | ✅ Running | 2/2 replicas |
| aither-redis-rate-limit | ✅ Running | Redis 7 |
| aither-identity | ✅ Running | OAuth + LDAP |
| aither-ai-platform | ✅ Running | Platform service |

### Nodes

| Node | Status | GPU |
|---|---|---|
| N8 (40.51) | ✅ Ready | 2× RTX 6000, both used by 14B TP=2 |
| N7 (40.50) | ✅ Ready | 2× RTX 6000, GPU#0 used by 32B, GPU#1 idle |

---

## Confirmed Working (from prior external audit)

Per GitHub Connector verification (prior session):
- Branch `aither-v2` confirmed at `5cdb43b`
- R6 history verified append-only
- Full WUI: 28/28 passed
- Availability runtime: Internet Zone 240/240 HTTP 200, Test Zone 240/240 HTTP 200
- 0 DNS/TLS/timeout/connection failures
- Intervals 0.8–1.2s: 100%

---

## Known Defects (current checkpoint)

| # | Defect | Severity | Source |
|---|---|---|---|
| 1 | **N7 GPU#1 idle** — 32B TP=2 should use both GPUs; only GPU#0 shows 21,865 MB | 🔴 HIGH | nvidia-smi on N7 |
| 2 | flink-taskmanager CrashLoopBackOff (1072 restarts) | 🟡 MEDIUM | aiops namespace |
| 3 | No GitHub push of emergency commits | 🔴 HIGH | Addressed by this checkpoint |
| 4 | Stale pods in cluster (test-curl*, tmp-curl*, node-debugger) | 🟢 LOW | Cleanup backlog |
| 5 | 32B model duplicated on N7 and N8 (38 GB wasted) | 🟢 LOW | Disk space |

---

## Historical Unresolved Findings

> The following findings are from prior audit stages (R6) and remain unresolved.
> They are NOT the primary focus of the current emergency.

| # | Finding | Source |
|---|---|---|
| H1 | TestBETA01 — revoked API key returned HTTP 200 instead of 401/403 | R6 Track A, Firefox Test Zone |
| H2 | Credential rotation evidence absent (3 files: headers only) | R6 blocker #1 |
| H3 | Raw logs absent (credential rotation, old credential rejection, session invalidation) | R6 blocker #2 |
| H4 | Gitleaks classification heuristic (auto-remediated without runtime check) | R6 blocker #3 |
| H5 | Commit J: model-switch contract not restored | R6 blocker #5 |
| H6 | Probe contract incomplete | R6 blocker #6 |
| H7 | Probe unit JUnit R6 absent | R6 blocker #7 |
| H8 | Fresh-clone R6 evidence absent | R6 blocker #8 |
| H9 | Acceptance Matrix absent | R6 blocker #9 |
| H10 | Behavioral Compliance Checklist absent | R6 blocker #10 |
| H11 | Placeholder Scan evidence absent | R6 blocker #11 |
| H12 | Final gate script absent | R6 blocker #12 |
| H13 | Mandatory Markdown files contain only headers | R6 blocker #13 |
| H14 | Final report: 9/10 Track A + Critical:0 — incorrect classification | R6 blocker #14 |

> These findings require a separate dedicated investigation (R7 or later stage).
> They are NOT being addressed in the current emergency.

---

## Risks

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| N7 GPU#1 idle means 32B running on single GPU (degraded) | HIGH | HIGH | Investigate immediately after checkpoint |
| Emergency commits not yet externally audited | HIGH | MEDIUM | This report enables audit |
| Node labels not in Git (drift risk) | MEDIUM | MEDIUM | Documented, reconcile post-emergency |
| flink-taskmanager down (aiops monitoring gap) | LOW | LOW | Non-blocking, fix post-emergency |
| 14B on N8 — if N8 fails, no 14B fallback to N7 | LOW | MEDIUM | Acceptable for emergency, revert plan documented |

---

## Unverified Claims

The following claims from emergency operations have NOT been independently verified:

1. "Chat 14B '2+2 equals 4' returned in 0.48 sec" — single manual test, not systematic
2. "Chat 32B 'Paris…' returned in 0.63 sec" — single manual test, not systematic
3. "All 18 documentation files return 200 OK with correct charset" — rapid curl check, not systematic
4. "Admin login works with owner-r5" — manual test, no automated verification

These should be systematically verified during post-emergency reconciliation.

---

## Next Steps After Emergency

1. **External audit** of this checkpoint (required before continuing)
2. **Investigate N7 GPU#1 idle** — TP=2 anomaly on 32B
3. **Resume R7-R5-C3** — continue corrective implementation from Direction 18
4. **Post-emergency reconciliation** — align K8s manifests with Git, add node labels to manifests
5. **Address historical R6 blockers** — in a separate dedicated stage
6. **Cleanup** — remove stale pods, resolve flink-taskmanager, deduplicate 32B model

---

## Request to Architect

```
REQUEST: External audit of Emergency Checkpoint R7-R5-EMG-01-CHECKPOINT-01

Actions requested:
1. Verify all 5 emergency commits via GitHub Connector (after push)
2. Confirm fast-forward chain from T0 (5cdb43b)
3. Review runtime-only changes (N8 label, BFF timeout, docs CM recovery)
4. Assess whether EMERGENCY MODE can be lifted
5. Authorize (or deny) resumption of R7-R5-C3
6. Confirm current status: U1.3-OPS-R7-R5 IN PROGRESS, R7-R5-C3 PAUSED

Hermes does NOT claim:
- R7 completed
- D18 completed
- Security incident closed
- TestBETA01 resolved
- Ready for user handover
```

---

**End of report. Awaiting external audit.**
