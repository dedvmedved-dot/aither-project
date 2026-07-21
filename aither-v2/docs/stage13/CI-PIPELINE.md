# Aither / AI Hermes MVP
# CI Pipeline — Stage 13 Continuous Verification

## Overview

The CI pipeline automates key RC1 verification checks on every `push`, `pull_request`,
and on `workflow_dispatch` (manual trigger).

## Workflow Structure

**File:** `.github/workflows/continuous-verification.yml`

The workflow is organised as **6 independent jobs** that run in parallel.
All jobs must pass for the pipeline to succeed.

| Job | Purpose | Fail action |
|---|---|---|
| **shell-syntax** | Validate bash script syntax (`bash -n`) | FAIL |
| **shellcheck** | Static analysis via ShellCheck (optional) | Informational only |
| **secrets-scan** | Scan for hardcoded secrets | FAIL |
| **repo-cleanliness** | Check git whitespace/formatting (`git diff --check`) | FAIL |
| **doc-consistency** | Verify RC1 release documents exist | FAIL |
| **acceptance-tests** | Run dnsPolicy fail-closed validation | FAIL |

## Job Details

### 1. Shell Syntax

```bash
bash -n scripts/check-gateway-32b.sh
bash -n scripts/test-gateway-32b-e2e.sh
bash -n scripts/test-check-gateway-dns-policy.sh
```

Validates that all shell scripts have correct syntax before execution.

### 2. ShellCheck (Optional)

If `shellcheck` is available on the runner:
```bash
shellcheck scripts/*.sh
```

If unavailable — outputs an informational notice and proceeds.

### 3. Secrets Scan

```bash
bash scripts/scan-secrets.sh
```

Runs the Aither Secret Scanner that checks for:
- Hardcoded JWT secrets in portal/bff/
- Hardcoded ADMIN_JWT_SECRET fallback
- docker-compose inline secrets
- Hardcoded PG_PASSWORD
- REPLACE_ME placeholders
- `.env` gitignore status

### 4. Repository Cleanliness

```bash
git diff --check
```

Detects whitespace errors and formatting violations.

### 5. Documentation Consistency

Checks that all required RC1 release documents exist under `docs/release/`:
- `RC1-RELEASE-MANIFEST.md`
- `RC1-RELEASE-NOTES.md`
- `RC1-REPRODUCIBILITY.md`
- `RC1-VERIFICATION-MATRIX.md`

### 6. Acceptance Tests

```bash
bash scripts/test-check-gateway-dns-policy.sh
```

Runs isolated dnsPolicy fail-closed validation.
Expected: 6 PASS, 0 FAIL.

## Local Execution

Run all checks manually before committing:

```bash
cd aither-v2/

# Shell syntax
bash -n scripts/check-gateway-32b.sh
bash -n scripts/test-gateway-32b-e2e.sh
bash -n scripts/test-check-gateway-dns-policy.sh

# ShellCheck (if installed)
command -v shellcheck && shellcheck scripts/*.sh

# Secrets scan
bash scripts/scan-secrets.sh

# Repository cleanliness
git diff --check

# Acceptance tests
bash scripts/test-check-gateway-dns-policy.sh

# Overall status
git status
```

## Interpreting Results

- **All jobs green (exit 0):** Pipeline passed — all quality gates satisfied.
- **Any job red (exit != 0):** Pipeline failed — investigate the failing job's logs.
- **ShellCheck yellow:** Non-blocking — informational only.

## Scope

- **Changed by this pipeline:** `.github/workflows/`, `scripts/`, `docs/`, `README`
- **Never changed by CI:** Gateway runtime, Kubernetes manifests, inference, auth, DNS, kubelet, production configuration.
