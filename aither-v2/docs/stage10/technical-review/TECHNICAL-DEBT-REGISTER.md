# TECHNICAL-DEBT-REGISTER.md

**Project:** Aither / AI Hermes MVP  
**Stage:** Stage 10 — RC1 Gate  
**Document:** Technical Debt Register  
**Date:** 2026-07-20

---

## Purpose

Complete register of technical debt items identified in the aither-v2 repository.

---

## Critical Items

| ID | Description | Location | Risk | Recommendation |
|---|---|---|---|---|
| TD-CRIT-01 | **Hardcoded JWT secret in source code.** `portal/bff/src/server.ts:13` contains `"aither-dev-jwt-secret-2026"`. `portal/server.ts:1458` defaults to `"aither-admin-secret"`. `portal/docker-compose.yml:27` sets `JWT_SECRET: "dev-jwt-secret-change-me"`. These are committed secrets that allow token forgery. | `portal/bff/src/server.ts:13` `portal/server.ts:1458` `portal/docker-compose.yml:27` | Critical — credential compromise, token forgery, unauthorized access | Remove hardcoded secrets. Use environment variables only. Rotate secret. |
| TD-CRIT-02 | **Invite code committed as plaintext.** `portal/docker-compose.yml:30` contains `INVITE_CODE: "aither-2026"`. | `portal/docker-compose.yml:30` | Critical — unauthorized registration possible | Move INVITE_CODE to env-only. Rotate the value. |
| TD-CRIT-03 | **Gateway ClusterIP workaround not committed.** The runtime fix changing nginx upstream from DNS hostname to ClusterIP `10.99.3.103` was applied but never committed to the manifest. After redeployment, the 32B gateway will fail again on node n7 (MissingClusterDNS). | `nginx-gateway-32b-hardened.yaml:21` (uses hostname, runtime patched to ClusterIP) | Critical — next redeployment breaks 32B access | Commit the ClusterIP or fix CoreDNS scheduling on node n7. |

## Major Items

| ID | Description | Location | Risk | Recommendation |
|---|---|---|---|---|
| TD-MAJ-01 | **Deploy script namespace mismatch.** `scripts/deploy.sh` deploys to `default` namespace, while aither-v2 manifests use `aither-inference`. The deploy script also references deployments (`vllm-qwen`, `vllm-qwen32b`) absent from aither-v2 manifests. | `scripts/deploy.sh:9,49-59` | Major — deploy script will fail or deploy to wrong namespace | Separate aither-v2 deploy script or parameterize namespace. |
| TD-MAJ-02 | **BFF ConfigMap minification.** The `bff-mvp.yaml` contains a minified/obfuscated copy of `app.py` (single-letter variables, no comments, 1-line functions). The source `tools/bff/app.py` is clear and documented. Any fix must be applied to BOTH files. Sync drift risk. | `bff-mvp.yaml:7-253` (minified) vs `tools/bff/app.py` (clean) | Major — maintenance burden, high drift risk | Generate ConfigMap from source file during CI/CD rather than maintaining two copies. |
| TD-MAJ-03 | **No automated tests.** Zero unit tests, integration tests, or E2E tests exist in the repository. | Entire repository | Major — regressions cannot be detected automatically | Add test framework. Start with BFF endpoint tests using pytest + httpx. |
| TD-MAJ-04 | **Gateway image tag not pinned by digest.** `nginx:alpine` (version tag) is used instead of a digest-pinned image. Over time, the `latest` equivalent can break behavior. | `nginx-gateway-32b-hardened.yaml:54` | Major — non-reproducible deployments | Pin by digest: `nginx:alpine@sha256:...` |
| TD-MAJ-05 | **nginx-gateway-32b uses incomplete securityContext.** `nginx` image requires `CHOWN`, `SETGID`, `SETUID` capabilities. `runAsNonRoot` is explicitly NOT set. ReadOnlyRootFilesystem not enabled. | `nginx-gateway-32b-hardened.yaml:55-57` | Major — elevated container privileges | Use distroless nginx image or document the nginx requirement. |

## Minor Items

| ID | Description | Location | Risk | Recommendation |
|---|---|---|---|---|
| TD-MIN-01 | **CI pipeline does not cover BFF or Portal.** GitHub Actions CI lints only `gateway/` Python files and `scripts/` shell scripts. BFF (`tools/bff/`) and Portal (`tools/portal/`) have no automated validation. | `.github/workflows/ci.yml` | Minor — code quality gaps for BFF/Portal | Add ruff/pyflakes checks for `tools/bff/` and prettier/eslint for Portal JS. |
| TD-MIN-02 | **Redis securityContext empty.** `redis-rate-limit.yaml:48` has `securityContext: {}`. No resource limits for capabilities, no runAsNonRoot. | `redis-rate-limit.yaml:48` | Minor — better defaults available | Add `runAsNonRoot: true`, cap drop. |
| TD-MIN-03 | **Portal source file duplication.** The `portal/dist/` directory contains compiled JS (`server.js`, `api-gateway.js`) alongside TypeScript sources. `dist/` files appear to be committed manually — no build pipeline. | `portal/dist/` | Minor — manual compilation, outdated dist files | Add .gitignore for dist/, automate build. |
| TD-MIN-04 | **No Helm chart or kustomize overlay.** All manifests are raw YAML with hardcoded namespaces and values. No environment overlays (dev/staging/prod). | All manifests under `aither-v2/manifests/` | Minor — limited scalability for multi-env | Consider Kustomize once multi-environment is needed. |
| TD-MIN-05 | **Rate limit reset TTL not directly observable.** Rate limit TTL resets with each new request in the same window. Window expiry is confirmed only by manual Redis flush. | `app.py:98-100` | Minor — cosmetic/observability | Add Redis TTL tracking on health endpoint for observability. |
| TD-MIN-06 | **SSL/TLS not configured for any endpoint.** `secure=False` in BFF session cookie. Gateway, BFF, Portal all use plain HTTP. | `app.py:420`, all Service manifests | Minor (accepted for MVP internal scope) | Add HTTPS once external access is required. |
| TD-MIN-07 | **GitHub CI fails silently on manifest validation.** `ci.yml:53` uses `|| true` which hides schema validation errors. | `.github/workflows/ci.yml:53` | Minor — false sense of security | Remove `|| true` and fix validation properly. |
| TD-MIN-08 | **Pod security context minimal.** BFF has `runAsNonRoot: true` but Portal does not. | `portal-mvp.yaml:357` (nginx:alpine) | Minor — hardening opportunity | Add securityContext to portal Deployment. |

## Deferred Items

| ID | Description | Status | Reference |
|---|---|---|---|
| TD-DEF-01 | `AITHER-QWEN38-GGUF-LLAMACPP-R1-C1-QUALIFICATION-CLOSURE` — R1 Q5 GGUF qualification closure gaps: (1) retained lab manifest uses floating image `server-cuda` instead of immutable digest; (2) R1 evidence contains only one deterministic 60K semantic run vs required >=3. | DEFERRED (by Architect) | `docs/evidence/AITHER_QWEN38_GGUF_LLAMACPP_QUALIFICATION_R1.md` |

---

## Summary

| Severity | Count |
|---|---|
| Critical | 3 |
| Major | 5 |
| Minor | 8 |
| Deferred | 1 |
| **Total** | **17** |

**Note:** This register documents objectively verifiable findings only. Each item references specific file locations. No speculative or unverifiable items are included.
