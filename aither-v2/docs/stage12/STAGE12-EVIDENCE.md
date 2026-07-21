# Stage 12 — Release Hardening & Reproducibility (RC1 Freeze) — Evidence

## 1. Repository Freeze Audit

### Structure Check

- All files organised under `docs/`, `manifests/`, `scripts/`, `services/`, `tools/`, `release/`
- No temporary files (`.tmp`, `.bak`, `*~`, `.DS_Store`, `.swp`)
- No debug artifacts
- TODO/FIXME/HACK/XXX: **0 findings** (clean)

### Duplicate Directory Note

Historical duplicate directories exist (`05-bff`/`05-bff-api`, `06-rate-limiting`/`06-redis-rate-limit`,
`07-portal`/`07-portal-spa`, `08-monitoring`, `09-gateway-replica-health`/`09-model-provenance`).
These contain evidence from different stages and are preserved as-is.

---

## 2. Documentation Consistency

### SHA References

- `docs/stage11/DNS-N7-EVIDENCE.md` had a placeholder `(next commit SHA)` → **fixed** to `3482249`
- All other SHA references in stage10/11 docs are consistent

---

## 3. Created Documents

| Document | Path | Description |
|---|---|---|
| RC1 Reproducibility Guide | `docs/release/RC1-REPRODUCIBILITY.md` | 10-step "from scratch" deployment |
| RC1 Release Manifest | `docs/release/RC1-RELEASE-MANIFEST.md` | Repository info, commit chain, checklist |
| RC1 Verification Matrix | `docs/release/RC1-VERIFICATION-MATRIX.md` | 38 requirements with verification methods |
| RC1 Release Notes | `docs/release/RC1-RELEASE-NOTES.md` | Major changes, fixed defects, migration notes |
| Stage 12 Evidence | `docs/stage12/STAGE12-EVIDENCE.md` | This document |

---

## 4. Verification Checks

| Check | Result |
|---|---|
| `git diff --check` | Clean |
| `git status` | Clean (only new stage12 docs + fixed SHA in dns-n7-evidence) |
| `bash -n scripts/check-gateway-32b.sh` | OK |
| `bash -n scripts/test-gateway-32b-e2e.sh` | OK |
| `bash -n scripts/test-check-gateway-dns-policy.sh` | OK |
| `bash -n scripts/scan-secrets.sh` | OK |

---

## 5. Reproducibility Verification

The `docs/release/RC1-REPRODUCIBILITY.md` contains:

- Hardware requirements (2 GPU nodes, A100 80GB)
- Software versions (Kubernetes v1.33.5, containerd 2.2.1)
- Required tools (kubectl, curl, base64, bash)
- 10-step deployment sequence
- Expected outcomes table
- Known limitations

The guide is self-contained and does not reference internal knowledge.

---

## 6. Compliance

- ✅ No runtime changes to Gateway, manifests, kubelet, DNS, auth, or security
- ✅ Only documentation and release automation changes
- ✅ All changes within Stage 12 scope
- ✅ No acceptance status claimed
