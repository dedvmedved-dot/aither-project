# PART2-GATEWAY-DNS-REMEDIATION-REPORT.md

**Project:** Aither / AI Hermes MVP
**Stage:** Stage 10 — Implementation Part 2 Remediation
**Document:** Gateway DNS Remediation Report (Updated)
**Date:** 2026-07-20

---

## 1. Problem Statement

Gateway ConfigMap uses DNS hostname `vllm-32b-gptq.aither-inference.svc` for upstream. On node `n7`, `kubelet` emits `MissingClusterDNS`, falling back to `Default` DNS policy (8.8.8.8). This causes nginx to fail DNS resolution at startup → CrashLoopBackOff.

A runtime workaround (ClusterIP `10.99.3.103`) was manually patched but never committed to Git — creating a **runtime-only change** not reflected in source control.

## 2. Root Cause

**kubelet on node `bootsmam-k8s-clnt01-n7-gpu` does not apply the `clusterDNS: [10.96.0.10]` from the `kubelet-config` ConfigMap.** Although the ConfigMap exists with correct values, kubelet on n7 uses a local config file or command-line argument that overrides it. SSH to n7 was unavailable to confirm the exact cause.

Evidence:
- `MissingClusterDNS` event re-occurred 42,507+ times over 6d21h
- Both CoreDNS pods on n8 only (none on n7)
- Gateway pod on n7 has `resolv.conf` pointing to `8.8.8.8` instead of `10.96.0.10`
- Pod on n8 has correct `nameserver 10.96.0.10`

## 3. Solution Selected

**Variant B** (documented, sustainable workaround):

1. **Changed `dnsPolicy` from `ClusterFirst` to `Default`** — pods on n7 use host's `/etc/resolv.conf`. This allows nginx to start and use the hardcoded ClusterIP.
2. **Updated nginx.conf with stable ClusterIP** `http://10.99.3.103:8000` — this is the vllm-32b-gptq Service ClusterIP, which is stable for the lifetime of the Service.
3. **Added `resolver 10.96.0.10 valid=30s`** to nginx config — if/when ClusterDNS is fixed, nginx can dynamically resolve hostnames (future-proofing).
4. **Added startupProbe + readinessProbe + livenessProbe**:
   - `startupProbe`: checks `/healthz` (local nginx endpoint, 150s timeout for model loading)
   - `readinessProbe`: checks `/health` (upstream health via vLLM)
   - `livenessProbe`: checks `/healthz` (local nginx — **does NOT depend on vLLM**, avoids restart loop when upstream is temporarily unavailable)
5. **Added `/healthz` local nginx location** — returns 200 without upstream dependency. Used by startup and liveness probes.
6. **Committed the runtime ConfigMap to Git** — no more drift between Git and runtime.

### Probe Design Rationale

| Probe | Endpoint | Depends on vLLM? | Purpose |
|---|---|---|---|
| startupProbe | `/healthz` (local) | No | Allow nginx to start even before vLLM is ready |
| readinessProbe | `/health` (upstream) | Yes | Only route traffic when 32B is actually available |
| livenessProbe | `/healthz` (local) | No | Restart nginx if local process dies, NOT if vLLM is temporarily slow |

This ensures resilience: a temporary vLLM outage does NOT trigger nginx restart (liveness uses /healthz), while traffic is correctly drained when vLLM is unavailable (readiness uses /health).

## 4. Why Not Variant A

Variant A (fix CoreDNS scheduling on n7) requires:
- SSH access to n7 to fix kubelet `--cluster-dns` flag
- Or: editing kubelet systemd unit on n7

SSH to n7 was unavailable during the implementation window. Variant B is fully functional and reproducible without node access. The DNS-N7-01 finding remains PARTIAL — full resolution requires node-level access.

## 5. Closed Findings

| Finding ID | Description | Status |
|---|---|---|
| TD-CRIT-03 | Gateway ClusterIP workaround not committed | ✅ **CLOSED** |
| DNS-N7-01 | MissingClusterDNS on node n7 | ⚠️ **PARTIAL** (requires node access) |
| GW-RUNTIME-CM-01 | ConfigMap drift between GitHub and runtime | ✅ **CLOSED** |
| IMPL-HOST-01 | Hostname-based upstream breaks on n7 | ✅ **CLOSED** |
| GW-32B-REPLICA-01 | Replica health / CrashLoopBackOff | ✅ **CLOSED** (verified 2/2 Running) |
| GW-CLUSTERIP-01 | Hardcoded ClusterIP workaround | ✅ **CLOSED** (committed and documented) |

### Audit Findings (ChatGPT Remediation)

| Finding | Status | Evidence |
|---|---|---|
| Missing token allowed exit 0 | ✅ **CLOSED** | `fail()` when token unavailable; exit 1 |
| Health test error allowed WARN | ✅ **CLOSED** | `fail()` on health test errors instead of `warn()` |
| Running used instead of Ready | ✅ **CLOSED** | Pods checked with `phase=Running + Ready=True` |
| jq dependency mismatch | ✅ **CLOSED** | `jq` removed from requirements; no `jq` usage |

### Acceptance Gate Strictness Follow-up

The following improvements were made in commit `392c323`:

1. **Authenticated tests are mandatory**: `GATEWAY_TOKEN` is resolved from env or K8s Secret. If unavailable → `FAIL`, exit 1. Authenticated tests always run.
2. **Health test failures are FAIL**: `/healthz` and `/health` errors use `fail()` (not `warn()`). Command failures, timeouts, and non-200 responses all increment `FAIL`.
3. **Pod readiness uses Ready condition**: Both `phase=Running` and `Ready=True` must be true for each pod.
4. **`jq` dependency removed**: All JSON parsing uses `grep`/`sed`/`awk`. Requirements line lists only actually used commands: `kubectl, curl, base64, grep, awk, sed`.
5. **Dependency check**: Missing required commands are reported as `FAIL`.
6. **Negative tests confirmed**:
   - No token (`GATEWAY_SECRET_NAME=nonexistent`): FAIL=3, exit code 1
   - Invalid token (`invalid-test-token`): FAIL=2, exit code 1
   - Valid token: PASS=32, FAIL=0, exit code 0

### Completion Model Consistency Follow-up

This commit adds mandatory validation that the `model` field in the `/v1/completions` response strictly equals the requested model. Implemented via `validate_response_model()` function with self-test mode. See evidence for positive and negative test results.

## 6. Changed Files

| File | Change |
|---|---|
| `aither-v2/manifests/mvp-roadmap/04-gateway/nginx-gateway-32b-hardened.yaml` | **Modified**: dnsPolicy→Default, ClusterIP upstream, resolver, livenessProbe, /healthz endpoint |
| `aither-v2/scripts/check-gateway-32b.sh` | **Rewritten**: 27 comprehensive checks, proper FAIL/WARN, no jq dependency |
| `aither-v2/scripts/test-gateway-32b-e2e.sh` | **New**: Standalone authenticated E2E test |
| `aither-v2/docs/stage10/implementation/PART2-GATEWAY-DNS-REMEDIATION-REPORT.md` | Updated report |
| `aither-v2/docs/stage10/implementation/PART2-EVIDENCE.md` | Updated evidence |
| `aither-v2/docs/stage10/implementation/PART2-RUNTIME-GIT-CONSISTENCY.md` | **Rewritten**: structural comparison methodology |

## 7. Kubernetes Naming vs Model ID

| Entity | Value |
|---|---|
| Kubernetes Service name | `vllm-32b-gptq` |
| Container/deployment label | `qwen-32b-gptq` |
| **Actual API model ID** | **`qwen-32b-base`** |

These are distinct. The API model ID must be obtained from `/v1/models`, not inferred from K8s resource names.

## 8. Remaining Risks

| Risk | Status | Mitigation |
|---|---|---|
| kubelet ClusterDNS on n7 unresolved | 🟡 Open | Requires SSH/node access to fix systemd unit |
| Gateway manifest uses ClusterIP — will break if Service is deleted/recreated | 🟢 Low | ClusterIP is stable; documented in DR plan |
| VPN instability affects remote operations | 🟡 Open | Known infrastructure limitation |

## 9. Conclusion

Gateway is now fully operational with verified reproducibility:

- **2/2 Running and Ready** — one pod on n7, one on n8
- **nginx -t** passes on both nodes
- **Returns 401** without auth token (correct)
- **Blocks /v1/chat/completions** with 422 (correct)
- **Routes authenticated 32B inference** through Gateway → vLLM with HTTP 200
- **ConfigMap committed to Git** — zero drift between Git, runtime, and running config
- **5-level upstream consistency**: Service ClusterIP = Git manifest = Runtime ConfigMap = Running nginx n7 = Running nginx n8
- **Diagnostic script**: 27/27 PASS, 0 FAIL, 0 WARN
- **Pod deletion recovery**: verified automatic

The `dnsPolicy: Default` + ClusterIP solution is sustainable for MVP. Full DNS fix on n7 requires node-level access and is tracked as DNS-N7-01 (PARTIAL).
