# RC1 Readiness Checklist

**Project:** Aither / AI Hermes MVP
**Document:** RC1 Final Acceptance — Release Candidate 1 Validation
**Base commit:** `36ddf4c210e19cef696e727b25b2ec8a01b568a5`
**Date:** 2026-07-21

---

## 1. Architecture

| Component | Requirement | Status | Notes |
|---|---|---|---|
| Gateway | nginx reverse proxy, 2 replicas (n7 + n8) | ✅ | `nginx-gateway-32b-hardened.yaml` |
| vLLM 14B | Qwen2.5-14B-Instruct, TP=2 on n8 | ✅ | Separate deployment manifest |
| vLLM 32B | qwen-32b-base, TP=2 on n7 | ✅ | `vllm-32b-gptq` Service name |
| Kubernetes | kubeadm cluster, 2 nodes (n7 worker, n8 CP+worker) | ✅ | Flannel CNI |
| DNS workaround | `dnsPolicy: Default` + ClusterIP upstream for n7 | ✅ | Documented in PART2 report |
| Gateway Service | ClusterIP, port 8000 | ✅ | `nginx-gateway-32b` Service |
| Upstream Service | `vllm-32b-gptq` ClusterIP | ✅ | Stable `10.99.3.103:8000` |

## 2. Security

| Check | Requirement | Status | Evidence |
|---|---|---|---|
| Auth passthrough | Gateway returns 401 without token | ✅ | Diagnostic script test |
| Gateway blocks chat | `/v1/chat/completions` returns 422 | ✅ | Diagnostic script test |
| No hardcoded secrets | JWT, invite codes, passwords removed | ✅ | Commit `48984a5`, scan-secrets.sh 6/6 |
| Git credential scan | No tokens/keys in repo | ✅ | Secret scan clean |
| Token never committed | `GATEWAY_TOKEN` from env or K8s Secret | ✅ | Both scripts use env/K8s Secret |
| Portal auth | Session + Bearer token auth | ✅ | BFF auth middleware |

## 3. Manifests

| Manifest | Path | Status |
|---|---|---|
| Gateway (ConfigMap + Deployment + Service) | `manifests/mvp-roadmap/04-gateway/nginx-gateway-32b-hardened.yaml` | ✅ |
| BFF | `manifests/mvp-roadmap/05-bff/bff-mvp.yaml` | ✅ |
| Portal | `manifests/mvp-roadmap/07-portal/portal-mvp.yaml` | ✅ |
| Rate limiting (Redis) | `manifests/mvp-roadmap/06-rate-limiting/redis-rate-limit.yaml` | ✅ |
| Auth secret example | `manifests/mvp-roadmap/07-auth-api/bff-auth-secret.example.yaml` | ✅ |

## 4. Scripts

| Script | Purpose | Status |
|---|---|---|
| `scripts/check-gateway-32b.sh` | Comprehensive diagnostic (27+ checks) | ✅ |
| `scripts/test-gateway-32b-e2e.sh` | Authenticated E2E completion test | ✅ |
| `scripts/scan-secrets.sh` | Hardcoded secret scanner | ✅ |

## 5. Runtime Verification

| Test | Expected | Actual | Evidence |
|---|---|---|---|
| Gateway pods | 2/2 Running + Ready | ✅ 2/2 | diagnostic script |
| Pod on n7 | Running + Ready=True | ✅ | diagnostic script |
| Pod on n8 | Running + Ready=True | ✅ | diagnostic script |
| nginx -t (n7) | syntax ok | ✅ | diagnostic script |
| nginx -t (n8) | syntax ok | ✅ | diagnostic script |
| /healthz (n7) | 200 | ✅ | diagnostic script |
| /healthz (n8) | 200 | ✅ | diagnostic script |
| /health (n7, upstream) | 200 | ✅ | diagnostic script |
| /health (n8, upstream) | 200 | ✅ | diagnostic script |
| No auth → 401 (n7) | 401 | ✅ | diagnostic script |
| No auth → 401 (n8) | 401 | ✅ | diagnostic script |
| Chat endpoint → 422 (n7) | 422 | ✅ | diagnostic script |
| Chat endpoint → 422 (n8) | 422 | ✅ | diagnostic script |
| Authenticated /v1/models | HTTP 200, model ID | ✅ | diagnostic script |
| Authenticated /v1/completions | HTTP 200, non-empty | ✅ | diagnostic script |
| Response model matches | Strict equality | ✅ | diagnostic script |
| Diagnostic script | FAIL=0, exit code 0 | ✅ | 3/3 consecutive runs |
| E2E test | PASS, exit code 0 | ✅ | test-gateway-32b-e2e.sh |

## 6. Upstream Consistency

| Level | Value | Match |
|---|---|---|
| Service ClusterIP | `10.99.3.103:8000` | ✅ |
| Git manifest upstream | `10.99.3.103:8000` | ✅ |
| Runtime ConfigMap upstream | `10.99.3.103:8000` | ✅ |
| Running nginx (n7) | `10.99.3.103:8000` | ✅ |
| Running nginx (n8) | `10.99.3.103:8000` | ✅ |

## 7. Negative Tests (Acceptance Gate)

| Test | Expectation | Result |
|---|---|---|
| GATEWAY_TOKEN unset | FAIL > 0, exit != 0 | ✅ |
| GATEWAY_TOKEN=invalid-test-token | FAIL > 0, exit != 0 | ✅ |
| Model mismatch (`wrong-model`) | FAIL > 0, exit != 0 | ✅ |
| Missing response model | FAIL > 0, exit != 0 | ✅ |
| Model match (`qwen-32b-base`) | PASS, exit 0 | ✅ |

## 8. Dependencies

| Tool | Required By | Included? |
|---|---|---|
| `kubectl` | All scripts | K8s environment |
| `curl` | All scripts | Standard |
| `base64` | Token resolution | Standard |
| `grep` | JSON parsing | Standard |
| `awk` | Upstream extraction | Standard |
| `sed` | HTTP code parsing | Standard |
| `bash` | Script execution | Standard |

## 9. Reproducibility Steps

1. **Clone repository:**
   ```bash
   git clone https://github.com/dedvmedved-dot/aither-project.git
   cd aither-project
   git checkout aither-v2
   ```

2. **Apply Gateway manifest:**
   ```bash
   kubectl apply -f manifests/mvp-roadmap/04-gateway/nginx-gateway-32b-hardened.yaml
   ```

3. **Create auth Secret:**
   ```bash
   kubectl -n aither-inference create secret generic aither-bff-auth \
     --from-literal=ADMIN_USERNAME=admin \
     --from-literal=ADMIN_PASSWORD_HASH=<hash> \
     --from-literal=AUTH_TOKEN_HASH_SECRET=<hash> \
     --from-literal=BFF_14B_UPSTREAM_AUTH_TOKEN=<token> \
     --from-literal=BFF_32B_GATEWAY_AUTH_TOKEN=<token> \
     --from-literal=SESSION_SECRET=<secret>
   ```

4. **Verify pods:**
   ```bash
   kubectl -n aither-inference rollout status deployment/nginx-gateway-32b --timeout=180s
   kubectl -n aither-inference get pods -o wide | grep gateway
   ```

5. **Verify Gateway:**
   ```bash
   bash scripts/check-gateway-32b.sh
   ```

6. **Run E2E test (with token):**
   ```bash
   export GATEWAY_TOKEN=<token>
   bash scripts/test-gateway-32b-e2e.sh
   ```

## 10. Acceptance Criteria Summary

| Category | Status |
|---|---|
| Architecture | ✅ All components documented |
| Manifests | ✅ All manifests valid and applied |
| Gateway DNS | ✅ Workaround in place (PARTIAL for ClusterDNS) |
| Authentication | ✅ Auth passthrough, 401 without token |
| Unsupported endpoints | ✅ 422 blocking |
| Authenticated inference | ✅ HTTP 200, model consistency verified |
| Pod lifecycle | ✅ Readiness, liveness, startup probes, pod deletion recovery |
| Runtime/Git consistency | ✅ Zero drift (kubectl diff, 5-level upstream check) |
| Acceptance gate | ✅ Fall-closed: fail on missing/invalid token, model mismatch |
| Secret hygiene | ✅ No credentials in repo |
| Diagnostics | ✅ 33/33 PASS, health checks, upstream, auth, E2E |
| Dependencies | ✅ Documented |

## 11. Known Limitations

```
DNS-N7-01 remains PARTIAL until kubelet clusterDNS configuration
on n7 is corrected with node-level access.
```

## 12. Commit Chain (Stage 10)

| Commit | Purpose |
|---|---|
| `36ddf4c` | Completion model consistency follow-up (HEAD) |
| `392c323` | Acceptance gate strictness follow-up |
| `47e56b7` | Gateway part 2 remediation |
| `e1fadc5` / `48984a5` | Part 1 security remediation |
| `1e97cd6` | Technical debt review |
| `37b0501` – `316f540` | Stage 10 documentation (00–10) |
