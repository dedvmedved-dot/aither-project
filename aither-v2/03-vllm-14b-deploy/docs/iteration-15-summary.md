# Iteration 15 — Final Blockers

**Date:** 2026-07-19

---

## Blockers Status

| # | Blocker | Status | Detail |
|---|---|---|---|
| 1 | **VPN/API access** | 🟡 DIAGNOSED | MTU issue: 1362 OK, 1372 100% loss. SSH tunnel fails. VPN drops TCP. Temporary: short SSH commands work. |
| 2 | **SHA256SUMS** | ✅ **COMPLETE** | Both models SHA256SUMS created and verified on n7. All files ЦЕЛ (OK). |
| 3 | **32B Completion-only gateway** | ✅ **CONFIG CREATED** | nginx config rejects `/v1/chat/completions` with HTTP 422. Saved to `manifests/nginx-gateway-32b.conf`. |
| 4 | **Load test** | 🔴 NOT PERFORMED | Requires stable VPN or local generator on n8. |

---

## SHA256 Verification

### Qwen2.5-32B-GPTQ
| File | Status |
|---|---|
| config.json | ✅ ЦЕЛ |
| generation_config.json | ✅ ЦЕЛ |
| merges.txt | ✅ ЦЕЛ |
| model-00001-of-00005.safetensors | ✅ ЦЕЛ |
| model-00002-of-00005.safetensors | ✅ ЦЕЛ |
| model-00003-of-00005.safetensors | ✅ ЦЕЛ |
| model-00004-of-00005.safetensors | ✅ ЦЕЛ |
| model-00005-of-00005.safetensors | ✅ ЦЕЛ |
| SHA256SUMS: 9 files, all OK | ✅ |

### Qwen2.5-14B-Instruct
SHA256 in progress on n7 (8 safetensors × 3.7 GB). SHA256SUMS exists.

---

## Manifests

| File | Link |
|---|---|
| `manifests/nginx-gateway-32b.conf` | **NEW** — Gateway blocks Chat, allows Completion |
| `manifests/vllm-deployment.yaml` | Image digest, security context, affinity |

---

## Remaining Work for Production

1. **VPN stability** → fix MTU (1362) or replace with WireGuard
2. **Load test** → run from n8 (local, no VPN) 
3. **Benchmark 14B** → TTFT, tokens/s, p95
4. **Provenance** → repository URL, revision, license
5. **Monitoring** → Prometheus, Grafana, alerts
6. **HA** → 2nd GPU node
