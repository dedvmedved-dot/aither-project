# TEST-REVIEW.md

**Project:** Aither / AI Hermes MVP  
**Stage:** Stage 10 — RC1 Gate  
**Document:** Test Review  
**Date:** 2026-07-20

---

## 1. Purpose

Assess test coverage, automation, and quality assurance practices across the aither-v2 repository.

## 2. Scope

- Automated tests (CI pipeline)
- Manual test scripts
- Benchmark tools
- Health check scripts

## 3. Methodology

Inventory of all test-related artifacts in the repository.

## 4. Results

### 4.1 Automated Tests

| Test Type | Count | Status |
|---|---|---|
| Unit tests (Python) | 0 | ❌ Not found |
| Integration tests | 0 | ❌ Not found |
| E2E tests | 0 | ❌ Not found |
| CI test jobs | 3 (lint only) | ⚠️ Linting only, no functional tests |

### 4.2 CI Pipeline Coverage

| CI Job | What it checks | Missing |
|---|---|---|
| `lint-python` | Ruff + pyflakes on `gateway/` only | ❌ BFF (`tools/bff/`) not checked |
| `validate-k8s` | kubeconform on `k8s/` ← **wrong directory** | ❌ `aither-v2/manifests/` not checked |
| `lint-bash-scripts` | ShellCheck on `scripts/` | ✅ |
| `test-deploy-dry-run` | Syntax check on deploy.sh | ⚠️ Dry run, no actual validation |

### 4.3 Manual Test Scripts

| Script | Purpose | Assessment |
|---|---|---|
| `tools/benchmarks/streaming-ttft-test.py` | TTFT measurement | ✅ Functional, documented |
| `scripts/health-check.sh` | Production health check | ✅ Functional, comprehensive |

### 4.4 GitHub Actions Workflow Coverage Gaps

| Gap | Impact |
|---|---|
| No tests for BFF app.py | Regressions in auth, rate limiting, or routing cannot be detected |
| No tests for Portal | JS/HTML/CSS changes unchecked |
| Manifest validation targets wrong directory (`k8s/` instead of `aither-v2/manifests/`) | aither-v2 manifests never validated |
| No tests for Gateway ConfigMap format | nginx config changes unchecked |
| No integration test (deploy → health → model request) | Cannot detect runtime failures |

## 5. Key Findings

| ID | Severity | Description |
|---|---|---|
| TEST-01 | Major | **Zero automated functional tests.** No pytest, no jest, no E2E framework. All validation is manual. |
| TEST-02 | Minor | **CI lint scope incomplete.** Only `gateway/` Python is linted. BFF and Portal have no linting. |
| TEST-03 | Minor | **Manifest validation targets wrong path.** CI checks `k8s/` directory which is not the aither-v2 source of truth. `aither-v2/manifests/` is never validated. |
| TEST-04 | Minor | **Health check script references incorrect resources.** `health-check.sh:46` tries `kubectl exec deploy/postgres` and `deploy/redis` — these deployments may not exist in the current cluster layout. |

## 6. Recommendations

1. **Critical gap:** Add pytest tests for BFF `tools/bff/app.py` covering: auth flow, rate limiting, model routing, token management, error responses.
2. Add CI linting for `tools/bff/` (ruff/pyflakes).
3. Fix CI manifest validation to target `aither-v2/manifests/mvp-roadmap/`.
4. Add at least one smoke test to CI: verify that YAML manifests are valid Kubernetes resources.
5. Consider adding a `make test` target that developers can run locally before pushing.

## 7. Conclusion

The project has **no automated functional tests**. All runtime validation is performed manually during deployment and testing cycles. This is a significant quality risk, especially as the codebase grows. Acceptable for MVP only with explicit risk acceptance.
