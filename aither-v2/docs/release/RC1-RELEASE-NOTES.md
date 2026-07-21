# Aither MVP RC1 — Release Notes

## Overview

Aither MVP RC1 is the first release candidate of the Aither AI inference
gateway platform. Built on Kubernetes (v1.33.5) with NVIDIA GPU acceleration,
it provides authenticated access to a quantized Qwen 32B GPTQ model through
an nginx-based gateway with health checks, rate limiting, and model consistency
validation.

---

## Major Changes

### Stage 10 — RC1 Readiness (base commit: `75931e6`)

- Published complete Stage 10 documentation (00–10)
- Conducted Technical Debt Review (50 findings: 9 Critical, 10 Major, 31 Minor)
- Portal security remediation: removed hardcoded secrets, switched to env-only
  with `fail-closed` pattern (`${VAR:?error}`)
- Created reproducible secret scanner (`scripts/scan-secrets.sh`)
- Gateway DNS workaround implemented for n7 (resolved in Stage 11)
- Acceptance gate strictness: mandatory auth checks are FAIL (not WARN)
- Model consistency: response model ID must exactly match requested model
- Created RC1 readiness checklist

### Stage 11 — DNS-N7-01 Closure (base commit: `db7781a`)

- **Root cause identified:** kubelet on n7 missing `--config` flag in systemd unit
- **Fix:** Added `--config=/var/lib/kubelet/config.yaml` to kubelet.service
- Removed `dnsPolicy: Default` workaround → switched to `ClusterFirst`
- Created DNS-N7-ROOTCAUSE, DNS-N7-REMEDIATION, DNS-N7-EVIDENCE docs
- Negative tests confirmed: ClusterFirst → PASS, everything else → FAIL
- Full regression: 33/33 PASS

### Stage 12 — Release Hardening (current commit: `3482249`)

- Repository freeze audit (no temporary/debug files)
- Documentation consistency fix (SHA references updated)
- Created RC1 reproducibility guide
- Created RC1 release manifest
- Created RC1 verification matrix (38 requirements)
- Created RC1 release notes (this document)

---

## Defects Fixed

| ID | Description | Stage |
|---|---|---|
| TD-CRIT-01 | Hardcoded JWT secrets in portal source code | Stage 10 |
| TD-CRIT-02 | Missing env-only credential fallback in portal | Stage 10 |
| DNS-N7-01 | kubelet on n7 not loading `--config`, causing DNS failure | Stage 11 |
| — | Acceptance gate fail-open (`\|\| echo "ClusterFirst"`) | Stage 11 |
| — | `dnsPolicy: Default` accepted as PASS | Stage 11 |

---

## Improvements

- **Fail-closed everywhere:** secrets, DNS policy, model consistency, auth
- **Negative test coverage:** isolated dnsPolicy test script
- **Evidence documentation:** per-stage evidence with reproduction commands
- **Verification matrix:** 38 requirements with verification methods

---

## Acceptance Gate Changes

The `scripts/check-gateway-32b.sh` diagnostic was hardened:

| Before | After |
|---|---|
| `\|\| echo "ClusterFirst"` (fail-open) | Separate error, empty, and value branches |
| `Default` accepted | `Default` → FAIL |
| Only 2 branches (if/else) | 5 branches (kubectl error / empty / ClusterFirst / Default / other) |

---

## Upgrade / Migration Notes

- **DNS:** After re-imaging a node, ensure kubelet flag `--config=/var/lib/kubelet/config.yaml`
  is present in systemd unit. This is not automatically applied from kubeadm.
- **Secrets:** All portal and gateway secrets must be supplied via Kubernetes Secrets
  or environment variables. No default credentials exist in the repository.
- **Gateway manifest:** `dnsPolicy: ClusterFirst` is mandatory.
  Do not revert to `Default`.

---

## Requirements

- Kubernetes v1.33.5
- containerd 2.2.1
- NVIDIA GPU Operator
- 2 GPU nodes
- CLI: kubectl, curl, base64, bash

---

## Documentation Index

| Document | Path |
|---|---|
| Reproducibility Guide | `docs/release/RC1-REPRODUCIBILITY.md` |
| Release Manifest | `docs/release/RC1-RELEASE-MANIFEST.md` |
| Verification Matrix | `docs/release/RC1-VERIFICATION-MATRIX.md` |
| Release Notes | `docs/release/RC1-RELEASE-NOTES.md` |
| RC1 Readiness Checklist | `docs/stage10/RC1-READINESS-CHECKLIST.md` |
| DNS-N7 Root Cause | `docs/stage11/DNS-N7-ROOTCAUSE.md` |
| DNS-N7 Remediation | `docs/stage11/DNS-N7-REMEDIATION.md` |
| DNS-N7 Evidence | `docs/stage11/DNS-N7-EVIDENCE.md` |

---

## Known Limitations

```
None.
```
