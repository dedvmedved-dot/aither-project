# Stage 18A — Security Scan Report

## Scope

Scanned files: all Stage 18A modified + new files:
- `services/*/Dockerfile` (3 files)
- `services/*/k8s/*.yaml` (3 files)
- `scripts/stage18a-*.sh` (5 files)
- `docs/stage18a/*.md` (6 files + 4 new reports)

## Secret Scan

**Tool:** `grep -RInE 'password|passwd|secret|token|api[_-]?key|private[_-]?key|BEGIN (RSA|OPENSSH|EC|DSA) PRIVATE KEY|Authorization:|Bearer |client_secret|access_key|secret_key'`

**Result:** ✅ CLEAN — no secrets found in Stage 18A scope.

**Note:** The following hits are **false positives** or **out of scope**:

| Finding | File | Real Secret? | Classification |
|---------|------|-------------|----------------|
| `password_hash` | `scripts/test-stage15-acceptance.sh:87` | ❌ | Test script, Stage 15, not Stage 18A scope |
| `password` | `scripts/bootstrap-admin.sh:13` | ❌ | Variable documentation, not hardcoded |
| `REPLACE_ME` | `services/identity/k8s/identity.yaml:16` | ❌ | Placeholder — explicitly marked `# Required: bcrypt hash of admin password` |
| `aither-identity-secret` | `services/identity/k8s/identity.yaml:7` | ❌ | Secret resource name reference, not secret value |
| `secretRef` | `services/identity/k8s/identity.yaml:66` | ❌ | Kubernetes API field, references external Secret object |
| `Authorization: Bearer` | `scripts/test-stage16-acceptance.sh` | ❌ | Test scripts with `***` masked tokens, not Stage 18A scope |

## Secret Scan (Extended — `git diff`)

**Command:** `git diff -- services/ Dockerfile scripts/ docs/`

**Result:** ✅ CLEAN — no secrets in the diff. All changes are:
- Image tag modifications
- `COPY --chown` and `USER 1000` Dockerfile instructions
- Documentation and automation scripts
- Registry URLs (non-sensitive internal addresses)

## Authentication & Credentials

| Item | Status | Notes |
|------|--------|-------|
| Hardcoded passwords | ✅ NONE | `REPLACE_ME` placeholder in identity.yaml — must be replaced before production deployment |
| API Keys in config | ✅ NONE | All configs reference external Secrets or env vars |
| Registry credentials | ✅ NONE | Registry has no auth (documented limitation for cluster-internal use) |
| SSH keys in repo | ✅ NONE | Not tracked |
| Service account tokens | ✅ NONE | `automountServiceAccountToken: false` in portal-backend.yaml |
| Kubeconfig in repo | ✅ NONE | Not tracked |

## Container Security

| Item | Status | Notes |
|------|--------|-------|
| Non-root user | ✅ YES | All 3 Dockerfiles: `USER 1000` |
| COPY with chown | ✅ YES | `COPY --chown=1000:1000 app/ ./app/` in all 3 Dockerfiles |
| runAsNonRoot | ✅ YES | In all 3 manifests |
| runAsUser/Group 1000 | ✅ YES | In all 3 manifests |
| Image from trusted source | ✅ YES | Self-built, stored in private registry |
| No privileged containers | ✅ YES | No `privileged: true`, no `securityContext.capabilities.add` |

## Findings Requiring Architect Attention

| ID | Severity | Finding | Recommendation |
|----|----------|---------|----------------|
| S-01 | LOW | Registry operates over HTTP without TLS | Acceptable for cluster-internal; add TLS if exposed externally |
| S-02 | LOW | Registry has no authentication | Acceptable for cluster-internal; add auth if required |
| S-03 | INFO | `REPLACE_ME` placeholder in identity.yaml | Must be replaced before production deployment |

**No critical or high-severity findings.**
