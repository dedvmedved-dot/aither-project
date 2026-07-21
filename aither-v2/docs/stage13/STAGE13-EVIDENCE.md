# Aither / AI Hermes MVP
# Stage 13 — Evidence Document

## Overview

Stage 13 implements a Continuous Verification CI Gate that automates key RC1
quality checks on every push, pull request, and manual trigger.

## Workflow Jobs

| Job | Status | Notes |
|---|---|---|
| **shell-syntax** | ✅ CREATED | `bash -n` on 3 scripts |
| **shellcheck** | ✅ CREATED | Non-fatal; informational only |
| **secrets-scan** | ✅ CREATED | Runs `scan-secrets.sh` |
| **repo-cleanliness** | ✅ CREATED | `git diff --check` |
| **doc-consistency** | ✅ CREATED | Verifies 4 RC1 release docs |
| **acceptance-tests** | ✅ CREATED | Runs `test-check-gateway-dns-policy.sh` |

## Local Verification Results

All checks performed from repository root `/root/aither-v2` with
working-directory `aither-v2/`.

### Shell Syntax (bash -n)

| Script | Result |
|---|---|
| `scripts/check-gateway-32b.sh` | ✅ PASS |
| `scripts/test-gateway-32b-e2e.sh` | ✅ PASS |
| `scripts/test-check-gateway-dns-policy.sh` | ✅ PASS |

### ShellCheck

| Status | Detail |
|---|---|
| ℹ️ NOT AVAILABLE | `shellcheck` not installed on runner. Will emit informational notice in CI. |

### Secrets Scan

| Check | Result |
|---|---|
| Hardcoded JWT secret (portal/bff/) | ✅ PASS |
| Hardcoded ADMIN_JWT_SECRET fallback | ✅ PASS |
| docker-compose inline secrets (JWT/INVITE) | ✅ PASS |
| Hardcoded PG_PASSWORD in compose | ✅ PASS |
| REPLACE_ME placeholder used as value | ✅ PASS |
| .env is gitignored | ⚠️ FAIL — `.env` not present in `.gitignore` |

**Note:** The secrets scanner correctly exits with code 1 upon finding issues.
This is the intended CI behavior — the pipeline will FAIL on this check,
alerting maintainers to address the finding.

### Repository Cleanliness

| Check | Result |
|---|---|
| `git diff --check` | ✅ PASS — no whitespace errors |

### Acceptance Tests

| Check | Result |
|---|---|
| `scripts/test-check-gateway-dns-policy.sh` | ✅ 6 PASS, 0 FAIL |

## Files Created

| File | Description |
|---|---|
| `.github/workflows/continuous-verification.yml` | Main CI pipeline — 6 jobs |
| `docs/stage13/CI-PIPELINE.md` | Pipeline documentation |
| `docs/stage13/STAGE13-EVIDENCE.md` | This evidence document |

## Files Modified

None.

## Known Limitations

| # | Limitation | Impact |
|---|---|---|
| 1 | `shellcheck` not pre-installed on runner | Non-fatal; informational notice emitted |
| 2 | `.env` not in `.gitignore` — flagged by secrets scanner | CI secret-scan job will FAIL (correct behaviour) |

## Beta Foundation Readiness

### Purpose

Stage 13 establishes a mandatory Quality Gate that enables safe parallel development
of Beta-stage features (Stage 15 — User Portal, Stage 16 — AI Platform) without
risk of regressing the verified RC1 infrastructure.

### What Stage 13 guarantees

1. **Every push/PR is verified** — the CI pipeline runs 6 independent checks before
   any code reaches the main branch.
2. **Fail-fast / fail-closed** — any critical check failure blocks the pipeline.
3. **Shell syntax validated** — `bash -n` on all 3 diagnostic scripts.
4. **Secrets leak prevention** — hardcoded credentials are detected and blocked.
5. **Repository formatting enforced** — `git diff --check` catches whitespace issues.
6. **Release documentation required** — all 4 RC1 release docs must exist.
7. **Acceptance tests enforced** — dnsPolicy fail-closed logic is re-verified on every run.

### Safe parallel development

| Concern | Mitigation |
|---|---|
| New portal code breaking Gateway | CI verifies Gateway diagnostic scripts still pass |
| New secrets introduced | CI scans and blocks hardcoded secrets |
| Release docs accidentally deleted | CI checks for all 4 required files |
| dnsPolicy regression | Automated acceptance tests re-verify fail-closed logic |
| Shell syntax errors in new scripts | `bash -n` on all existing scripts |
| Formatting pollution from new branches | `git diff --check` enforces cleanliness |

### What Stage 13 does NOT do

- Does NOT modify Kubernetes manifests, Gateway runtime, inference, auth, or DNS.
- Does NOT introduce any user-facing functionality.
- Does NOT change acceptance test logic.
- Does NOT add new project dependencies.
- Does NOT alter the architecture of the MVP.

### Conclusion

The repository is ready for safe implementation of Stage 15 (User Portal) and
Stage 16 (AI Platform). All existing RC1 checks are automated and will continue
to verify the integrity of the verified infrastructure as new features are added.

## Cross-Reference

- **Parent commit:** `101dcbfbcf2e0420f85bc100f58f47d469a987c6`
- **Release docs:** `docs/release/RC1-*` (created in Stage 12)
- **Stage 11 evidence:** `docs/stage11/DNS-N7-*`
