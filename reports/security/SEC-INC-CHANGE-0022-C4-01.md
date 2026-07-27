# SEC-INC-CHANGE-0022-C4-01 — SIEM Admin Key Exposure & Rotation

**Incident ID:** SEC-INC-CHANGE-0022-C4-01
**Severity:** CRITICAL
**Date:** 2026-07-28
**Detected by:** Code audit (CHANGE-0022-C5)
**Affected commits:** Initial SIEM deployment commit (aither-v2/deploy/siem/deployment.yaml)
**Change:** CHANGE-0022-C5

---

## Exposure

A known admin key was committed to the repository in the SIEM deployment manifest:

| File | Line | Value |
|---|---|---|
| `aither-v2/deploy/siem/deployment.yaml` | 53 | `siem-admin-key-change-me-in-production` |

The key was stored in the `aither-siem-auth` Kubernetes Secret (`SIEM_ADMIN_KEY`) in namespace `aither-inference` and used for authenticating all SIEM query API endpoints (`/events`, `/events/count`, `/events/summary`, etc.).

## Impact

- **Authentication bypass**: Anyone with access to the repository (internal or external) could query SIEM events, exposing security audit logs, billing events, and access patterns.
- **Data exposure risk**: SIEM logs contain sensitive information including organisation IDs, user IDs, billing amounts, and security violation details.
- **Compliance violation**: Hardcoded credentials in version control violate security best practices and regulatory requirements.

---

## Containment Actions

### 1. Key Rotation ✅

| Step | Action | Result |
|---|---|---|
| 1.1 | Generated new random admin key (64-char hex) | `openssl rand -hex 32` |
| 1.2 | Applied new key to k8s Secret | `kubectl -n aither-inference create secret generic aither-siem-auth` |
| 1.3 | Restarted SIEM deployment | Rolling restart, pod replaced |
| 1.4 | Verified old key rejected | `401 authentication_required` ✅ |
| 1.5 | Verified new key accepted | `200 OK` with event data ✅ |

### 2. SIEM Port Mismatch Fixed ✅

| Step | Action | Result |
|---|---|---|
| 2.1 | Discovered Gateway had SIEM_PORT=514 | SIEM receiver listens on UDP 1514 (configmap `SIEM_UDP_PORT=1514`) |
| 2.2 | Updated Gateway deployment env: `SIEM_HOST=aither-siem.aither-inference.svc`, `SIEM_PORT=1514` | Match SIEM configmap |
| 2.3 | Gateway rollout completed | 2/2 pods healthy with correct SIEM config |

### 3. Manifest Cleanup ✅

| Step | Action | Result |
|---|---|---|
| 3.1 | Updated `aither-v2/deploy/siem/deployment.yaml` — replaced hardcoded key with `REDACTED-ROTATED-SEE-INCIDENT-REPORT` | Key no longer in repository |
| 3.2 | Added security incident labels and annotations to Secret manifest | Traceability |
| 3.3 | Updated `aither-v2/deploy/gateway/deployment.yaml` — added `SIEM_HOST` and `SIEM_PORT` env vars | Correct port (1514) |

---

## SIEM Event Verification

After key rotation, 16 real SIEM events were generated via Gateway to verify end-to-end SIEM pipeline:

| # | Event Type | Record ID | Timestamp |
|---|---|---|---|
| 1 | `auth_success` | `9cdad0e71ddef86b` | 2026-07-27T22:39:05Z |
| 2 | `auth_failure` | `50ea9def3799166f` | 2026-07-27T22:39:05Z |
| 3 | `scope_denied` | `a44bb71dbe5754d0` | 2026-07-27T22:39:05Z |
| 4 | `rate_limit_exceeded` | `95d83e3731e2dc00` | 2026-07-27T22:39:05Z |
| 5 | `security_input_block` | `75957499b615eb30` | 2026-07-27T22:39:05Z |
| 6 | `security_output_block` | `f3409b10d02e65d9` | 2026-07-27T22:39:05Z |
| 7 | `billing_reserve` | `f2c721b98b497769` | 2026-07-27T22:39:05Z |
| 8 | `billing_settle` | `8b697614fc2ba451` | 2026-07-27T22:39:05Z |
| 9 | `billing_refund` | `2db0debda9cfbbd5` | 2026-07-27T22:39:05Z |
| 10 | `admin_drain` | `765c0a753e81a035` | 2026-07-27T22:39:05Z |
| 11 | `admin_undrain` | `caac20a8f2b2d925` | 2026-07-27T22:39:05Z |
| 12 | `upstream_timeout` | `3f151a7ce1ac14bc` | 2026-07-27T22:39:05Z |
| 13 | `upstream_error` | `34cf9e24dac12239` | 2026-07-27T22:39:05Z |
| 14 | `dependency_failure` | `4fd2bbf996514a49` | 2026-07-27T22:39:05Z |
| 15 | `vault_failure` | `f7a71ed16e9cdfef` | 2026-07-27T22:39:05Z |
| 16 | `rag_access_denied` | `d687acae528efd09` | 2026-07-27T22:39:05Z |

**Additional events:**
| 17 | `admin_action` (internal) | `ed9f176d820944ce` | 2026-07-27T22:39:05Z |
| 18 | `settlement_failure` | `ef76fca63c23484f` | 2026-07-27T22:39:05Z |

**Verification:** `GET /events/summary` → `all_expected_present: true`, `covered_total: 16`, `missing_types: []`

---

## Configuration Audit

### Before (vulnerable state)
```yaml
# aither-siem-auth Secret
SIEM_ADMIN_KEY: "siem-admin-key-change-me-in-production"

# Gateway env
SIEM_HOST: "aither-siem.aither-inference.svc.cluster.local"  # redundant FQDN
SIEM_PORT: "514"  # MISMATCH: SIEM listens on UDP 1514
```

### After (remediated state)
```yaml
# aither-siem-auth Secret (in-cluster only)
SIEM_ADMIN_KEY: <64-char random hex key, not committed>

# Gateway env
SIEM_HOST: "aither-siem.aither-inference.svc"
SIEM_PORT: "1514"  # matches SIEM_UDP_PORT in ConfigMap
```

---

## Remediation Policy

1. **No hardcoded secrets in manifests** — all secrets must be injected via k8s Secrets, never committed to git.
2. **Pre-commit secret scanning** — enable `gitleaks` or `detect-secrets` in CI pipeline.
3. **SIEM key rotation schedule** — rotate SIEM admin key every 90 days.
4. **Port consistency check** — add CI validation that Gateway SIEM_PORT matches SIEM ConfigMap SIEM_UDP_PORT.
5. **Secret annotation** — all Secrets must have `security-incident` label if they were part of an incident rotation.

---

## Credential Exposure Summary

| Field | Value |
|---|---|
| Credential value exposed | YES — committed to git (`siem-admin-key-change-me-in-production`) |
| Old credential invalidated | YES — returns `401 authentication_required` |
| New Secret fingerprint | `aither-siem-auth` (rotated 2026-07-28) |
| SIEM pod restarted | YES (1/1 healthy) |
| Gateway pods restarted | YES (2/2 healthy) |
| SIEM events verified | YES (18 events, 16 expected types covered) |
| Gateway SIEM port mismatch | FIXED (514 → 1514) |
