# PART2-GATEWAY-DNS-REMEDIATION-REPORT.md

**Project:** Aither / AI Hermes MVP
**Stage:** Stage 10 — Implementation Part 2
**Document:** Gateway DNS Remediation Report
**Date:** 2026-07-20

---

## 1. Problem Statement

Gateway ConfigMap uses DNS hostname `vllm-32b-gptq.aither-inference.svc` for upstream. On node `n7`, `kubelet` emits `MissingClusterDNS`, falling back to `Default` DNS policy (8.8.8.8). This causes nginx to fail DNS resolution at startup → CrashLoopBackOff.

A runtime workaround (ClusterIP `10.99.3.103`) was manually patched but never committed to Git.

## 2. Root Cause

**kubelet on node `bootsmam-k8s-clnt01-n7-gpu` does not apply the `clusterDNS: [10.96.0.10]` from the `kubelet-config` ConfigMap.** Although the ConfigMap exists with correct values, kubelet on n7 uses a local config file or command-line argument that overrides it. SSH to n7 was unavailable to confirm the exact cause.

Evidence:
- `MissingClusterDNS` event re-occurred 42,507+ times over 6d21h
- Both CoreDNS pods on n8 only (none on n7)
- Gateway pod on n7 has `resolv.conf` pointing to `8.8.8.8` instead of `10.96.0.10`
- Pod on n8 has correct `nameserver 10.96.0.10`

## 3. Solution Selected

**Variant B** (documented, sustainable workaround):

1. **Changed `dnsPolicy` from `ClusterFirst` to `Default`** — pods on n7 use host's /etc/resolv.conf. While this doesn't resolve K8s service names, it allows nginx to start and use the hardcoded ClusterIP.
2. **Updated nginx.conf with stable ClusterIP** `http://10.99.3.103:8000` — this is the vllm-32b-gptq Service ClusterIP, which is stable for the lifetime of the Service.
3. **Added `resolver 10.96.0.10 valid=30s`** to nginx config — if/when ClusterDNS is fixed, nginx can dynamically resolve hostnames (future-proofing).
4. **Added startupProbe + readinessProbe** — nginx health check on /health.
5. **Committed the runtime ConfigMap to Git** — no more drift between Git and runtime.

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

## 6. Changed Files

| File | Change |
|---|---|
| `aither-v2/manifests/mvp-roadmap/04-gateway/nginx-gateway-32b-hardened.yaml` | **Modified**: dnsPolicy→Default, ClusterIP upstream, resolver, probes |
| `aither-v2/scripts/check-gateway-32b.sh` | **New**: 14-check diagnostic script |
| `aither-v2/docs/stage10/implementation/PART2-GATEWAY-DNS-REMEDIATION-REPORT.md` | This report |
| `aither-v2/docs/stage10/implementation/PART2-EVIDENCE.md` | Evidence document |
| `aither-v2/docs/stage10/implementation/PART2-RUNTIME-GIT-CONSISTENCY.md` | Git/runtime consistency verification |

## 7. Remaining Risks

| Risk | Status | Mitigation |
|---|---|---|
| kubelet ClusterDNS on n7 unresolved | 🟡 Open | Requires SSH/node access to fix systemd unit |
| Gateway manifest uses ClusterIP — will break if Service is deleted/recreated | 🟢 Low | ClusterIP is stable; documented in DR plan |
| VPN instability affects remote operations | 🟡 Open | Known infrastructure limitation |

## 8. Conclusion

Gateway is now fully operational:
- 2/2 Running and Ready
- nginx -t passes on both nodes
- Returns 401 without auth token (correct)
- Blocks /v1/chat/completions with 422 (correct)
- Routes to 32B vLLM on n7
- ConfigMap committed to Git — zero drift
- Diagnostic script passes 14/14 checks

The `dnsPolicy: Default` + ClusterIP solution is sustainable for MVP. Full DNS fix on n7 requires node-level access and is tracked as DNS-N7-01 (PARTIAL).
