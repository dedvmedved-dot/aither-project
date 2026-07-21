# Aither MVP RC1 — Release Manifest

## Repository Information

| Field | Value |
|---|---|
| Repository | `dedvmedved-dot/aither-project` |
| Branch | `aither-v2` |
| Base baseline | `75931e6f68530d59fadd15061796bbc1a67c1f9a` |
| Current release HEAD | `3482249cf05cf019d09d1b9791d72473e584ada9` |
| Release URL | https://github.com/dedvmedved-dot/aither-project/tree/3482249 |

---

## Stage Overview

| Stage | Description | Status |
|---|---|---|
| Stage 09 | Gateway replica health / connector verified | PASSED WITH FINDINGS |
| Stage 10 | RC1 Final Acceptance & Release Candidate Validation | PASSED WITH FINDINGS |
| Stage 11 | DNS-N7-01 Closure & Acceptance Gate Hardening | COMPLETED |
| Stage 12 | Release Hardening & Reproducibility (RC1 Freeze) | CURRENT |

---

## Commit Chain (chronological)

| SHA | Description |
|---|---|
| `75931e6` | Baseline before Stage 10 |
| `316f540` | Stage 10 docs 00–01 |
| `ca9f95d` | Stage 10 docs 02–03 |
| `15a0b7f` | Stage 10 docs 04–05 |
| `30dec2a` | Stage 10 docs 06–07 |
| `a66afe8` | Stage 10 docs 08–09 |
| `37b0501` | Stage 10 doc 10 |
| `1e97cd6` | Technical Debt Review |
| `48984a5` | Part 1 security remediation (portal secrets) |
| `e1fadc5` | Part 1 whitespace fix |
| `47e56b7` | Part 2 gateway DNS remediation |
| `392c323` | Part 2 acceptance gate strictness |
| `36ddf4c` | Part 2 completion model consistency |
| `db7781a` | RC1 readiness checklist |
| `2846366` | Stage 11 DNS-N7-01 closure (kubelet config fix) |
| `3482249` | Stage 11 acceptance gate fail-closed fix |
| **Current** | **Stage 12 release documentation** |

---

## Changed Files Summary

- **Manifests:** Gateway deployment with `dnsPolicy: ClusterFirst`, probes, auth
- **Scripts:** `check-gateway-32b.sh` (33 checks, fail-closed), `test-gateway-32b-e2e.sh`, `scan-secrets.sh`
- **Docs:** Stage 10/11/12 documentation, deployment guides, evidence
- **Portal:** Security hardening (secrets → env-only)

---

## Known Limitations

```
None.
```

---

## Readiness Checklist

| Requirement | Status |
|---|---|
| Gateway health | ✅ Verified |
| Gateway auth | ✅ Verified |
| Model consistency | ✅ Verified |
| DNS resolution (ClusterFirst) | ✅ Verified |
| Pod readiness (both nodes) | ✅ Verified |
| Diagnostic script (33/33 PASS) | ✅ Verified |
| E2E test | ✅ Verified |
| Reproducibility documented | ✅ Verified |
| No hardcoded secrets | ✅ Verified |
| No temporary/debug files | ✅ Verified |
| Acceptance gate fail-closed | ✅ Verified |
