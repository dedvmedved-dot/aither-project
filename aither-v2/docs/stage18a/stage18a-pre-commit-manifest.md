# Stage 18A — Pre-Commit Manifest

## Repository State

| Field | Value |
|-------|-------|
| Repository | `git@github.com:dedvmedved-dot/aither-project.git` |
| Branch | `aither-v2` |
| HEAD before Stage 18A commit | `82fe433845f8487296033e80e249160b8f7a58d7` |
| Remote | `origin` → `dedvmedved-dot/aither-project` |
| Working directory | `/root/aither-v2/aither-v2/` |

## Planned Commit Files

| File | Change Type | Purpose | Category |
|------|-------------|---------|----------|
| `services/identity/Dockerfile` | Modified (5 insertions) | Add `COPY --chown=1000:1000`, `USER 1000` — non-root security fix | manifest |
| `services/portal-backend/Dockerfile` | Modified (4 insertions) | Add `COPY --chown=1000:1000`, `USER 1000` — non-root security fix | manifest |
| `services/ai-platform/Dockerfile` | Modified (5 insertions) | Add `COPY --chown=1000:1000`, `USER 1000` — non-root security fix | manifest |
| `services/identity/k8s/identity.yaml` | Modified (1 line) | Image tag update `:stage15` → `:stage18a-82fe433` + full registry URL | manifest |
| `services/portal-backend/k8s/portal-backend.yaml` | Modified (1 line) | Image tag update `:stage15` → `:stage18a-82fe433` + full registry URL | manifest |
| `services/ai-platform/k8s/ai-platform.yaml` | Modified (1 line) | Image tag update `:stage16` → `:stage18a-82fe433` + full registry URL | manifest |
| `scripts/stage18a-build-images.sh` | New | Build all 3 Stage 18A images with immutable tags | automation |
| `scripts/stage18a-transfer-artifact.sh` | New | Transfer image archives via rsync with SHA-256 verification | automation |
| `scripts/stage18a-push-images.sh` | New | Import into containerd, tag, push to persistent registry | automation |
| `scripts/stage18a-verify-registry.sh` | New | Verify registry status, CRI, nodes | automation |
| `scripts/stage18a-deploy-services.sh` | New | Kubectl apply + rollout wait for all 3 services | automation |
| `docs/stage18a/ARCHITECTURE.md` | New | Architecture overview (nodes, services, registry, containerd config) | documentation |
| `docs/stage18a/REGISTRY.md` | New | Registry configuration (systemd, API, images, hosts.toml, limitations) | documentation |
| `docs/stage18a/DEPLOYMENT.md` | New | Deployment guide with sequence, rollback, PV/PVC recovery | documentation |
| `docs/stage18a/RUNTIME-EVIDENCE.md` | New | Runtime evidence (pod status, node status, CRI, health checks) | evidence |
| `docs/stage18a/N8-CRI-RECOVERY.md` | New | CRI recovery diagnosis and fix (config_path vs mirrors) | documentation |
| `docs/stage18a/STAGE18A-EVIDENCE.md` | New | Comprehensive evidence summary for all Stage 18A phases | evidence |
| `docs/stage18a/stage18a-pre-commit-manifest.md` | New | This file — pre-commit manifest | report |
| `docs/stage18a/stage18a-regression-summary.md` | New | Regression test results | report |
| `docs/stage18a/stage18a-security-scan.md` | New | Security scan report | report |
| `docs/stage18a/stage18a-automation-validation.md` | New | Automation scripts validation | report |
| `docs/stage18a/stage18a-evidence-index.md` | New | Evidence index | report |

## Excluded Files

| File | Reason Excluded |
|------|-----------------|
| `scripts/bootstrap-admin.sh` | Stage 15 — not Stage 18A |
| `scripts/check-gateway-32b.sh` | Stage 16 — not Stage 18A |
| `scripts/scan-secrets.sh` | Stage 15 — not Stage 18A |
| `scripts/test-*.sh` | Stage 15/16/17 — not Stage 18A |
| All other files outside `services/*/Dockerfile`, `services/*/k8s/*.yaml`, `scripts/stage18a-*.sh`, `docs/stage18a/` | Not part of Stage 18A scope |

## Validation

| Check | Result |
|-------|--------|
| `git diff --check` | ✅ CLEAN — no whitespace errors |
| Secret scan (grep -RInE password/secret/token/api_key) | ✅ CLEAN — no real secrets in Stage 18A scope |
| Large-file scan (files >5MB) | ✅ CLEAN — none |
| Binary/archive scan (.tar, .tar.gz, .zip, .img, etc.) | ✅ CLEAN — none |
| Script syntax (`bash -n` all Stage 18A scripts) | ✅ ALL 5 SCRIPTS PASS |
| Script lint (`shellcheck`) | ⚠️ NOT INSTALLED — syntax check passed |
| Script idempotency review | ✅ SEE automation-validation.md |
| Regression | ✅ ALL TESTS PASS |
| Documentation consistency | ✅ REVIEWED — no contradictions |

## Known Limitations

1. **n7 `crictl` not installed** — kubelet pulls images correctly via CRI; `crictl` binary not available on n7 for manual pull verification.
2. **Stage 18A pods pinned to n8** — historical `nodeName` from Stage 15-16 persists in live Deployment objects. Does not affect functionality. Requires `kubectl patch` to enable multi-node scheduling.
3. **Portal-backend port-forward timeout from build host** — not a service defect. Kubelet confirms 200 OK on all probes. Root cause: intermittent K8s API connectivity from build host.
4. **`skip_verify = true` in hosts.toml** — registry operates over plain HTTP without TLS. Acceptable for cluster-internal deployment.
5. **Registry has no auth** — open for read/write on cluster network. Documented limitation.

## Approval State

```
COMMIT AUTHORIZATION: PENDING ARCHITECT APPROVAL
CONNECTOR AUDIT: PENDING
FINAL ACCEPTANCE: PENDING
```
