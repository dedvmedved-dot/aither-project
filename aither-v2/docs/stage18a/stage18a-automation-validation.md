# Stage 18A — Automation Scripts Validation

## Scripts Inventory

| Script | Shebang | Set Flags | Purpose |
|--------|---------|-----------|---------|
| `scripts/stage18a-build-images.sh` | `#!/usr/bin/env bash` | `set -euo pipefail` | Build 3 Docker images with immutable Stage 18A tag |
| `scripts/stage18a-transfer-artifact.sh` | `#!/usr/bin/env bash` | `set -euo pipefail` | Transfer image archives via rsync + SHA-256 verification |
| `scripts/stage18a-push-images.sh` | `#!/usr/bin/env bash` | `set -euo pipefail` | Import into containerd, tag, push to registry |
| `scripts/stage18a-verify-registry.sh` | `#!/usr/bin/env bash` | `set -euo pipefail` | Verify registry, CRI, nodes |
| `scripts/stage18a-deploy-services.sh` | `#!/usr/bin/env bash` | `set -euo pipefail` | Kubectl apply + rollout wait |

## Validation Results

| Check | build-images | transfer-artifact | push-images | verify-registry | deploy-services |
|-------|:---:|:---:|:---:|:---:|:---:|
| Executable bit | ✅ `-rwx--x--x` | ✅ `-rwx--x--x` | ✅ `-rwx--x--x` | ✅ `-rwx--x--x` | ✅ `-rwx--x--x` |
| Syntax (`bash -n`) | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS |
| `shellcheck` | ⚠️ NOT RUN — TOOL NOT INSTALLED | ⚠️ NOT RUN — TOOL NOT INSTALLED | ⚠️ NOT RUN — TOOL NOT INSTALLED | ⚠️ NOT RUN — TOOL NOT INSTALLED | ⚠️ NOT RUN — TOOL NOT INSTALLED |
| Error handling | ✅ `set -Eeuo pipefail` | ✅ `set -Eeuo pipefail` | ✅ `set -Eeuo pipefail` | ✅ `set -Eeuo pipefail` | ✅ `set -Eeuo pipefail` |
| Hardcoded secrets | ✅ NONE | ✅ NONE | ✅ NONE | ✅ NONE | ✅ NONE |
| Hardcoded credentials | ✅ NONE | ✅ NONE | ✅ NONE | ✅ NONE | ✅ NONE |
| Runtime data in repo | ✅ NONE | ✅ NONE | ✅ NONE | ✅ NONE | ✅ NONE |
| Idempotency safe | ✅ YES (docker build) | ✅ YES (rsync --partial) | ✅ YES (ctr import is idempotent) | ✅ YES (read-only) | ✅ YES (kubectl apply) |
| Dry-run available | ❌ N/A | ❌ N/A | ❌ N/A | ❌ N/A | ✅ YES (kubectl apply --dry-run=client) |
| Backup before modify | ✅ N/A (build only) | ✅ N/A (transfer only) | ✅ N/A (import/push only) | ✅ N/A (read-only) | ❌ N/A (kubectl applies over existing) |
| Rollback described | ✅ N/A | ✅ N/A | ✅ N/A | ✅ N/A | ✅ In DEPLOYMENT.md |
| Clear error messages | ✅ YES | ✅ YES | ✅ YES | ✅ YES | ✅ YES |
| Correct exit codes | ✅ YES (set -e) | ✅ YES (set -e) | ✅ YES (set -e) | ✅ YES (set -e) | ✅ YES (set -e) |
| Dependency check | ✅ Docker | ✅ rsync, ssh, zstd | ✅ ssh, zstd, ctr | ✅ ssh, curl, ctr, crictl | ✅ kubectl |

## Detailed Review

### `stage18a-build-images.sh`
- **Idempotent:** Yes — `docker build` reuses cache on unchanged context
- **Destructive:** No — builds only, no network state changes
- **Edge case:** If Docker daemon not running, `set -e` causes exit with clear error

### `stage18a-transfer-artifact.sh`
- **Idempotent:** Yes — `rsync --partial --append-verify` resumes interrupted transfers
- **Destructive:** No — only creates files in `/tmp/stage18e/` on destination
- **Edge case:** SHA-256 mismatch exits with code 1, preventing downstream corruption

### `stage18a-push-images.sh`
- **Idempotent:** Yes — `ctr images import` overwrites existing, `ctr images push` re-pushes
- **Destructive:** No — registry accepts duplicate pushes, no deletion
- **Edge case:** SSH connection failure handled by `ConnectTimeout=30`

### `stage18a-verify-registry.sh`
- **Idempotent:** Yes — read-only verification
- **Destructive:** No
- **Edge case:** Gracefully handles missing node via `||` fallback in `kubectl get nodes`

### `stage18a-deploy-services.sh`
- **Idempotent:** Yes — `kubectl apply` is idempotent by design
- **Destructive:** No — applies manifests, waits for rollout
- **Preflight:** ✅ Checks kubectl exists, cluster reachable, namespace exists, Secret exists, manifest files exist. Exits with code 1 on any failure.
- **Secret safety:** ✅ Fails immediately (exit 1) if `aither-identity-secret` does not exist. Does not create or apply secrets automatically.
- **Rollout handling:** ✅ Uses `kubectl rollout status ... --timeout=120s` without `|| echo WARNING`. On failure, outputs deployment name, `kubectl get deployment`, `kubectl get pods` for diagnostics, then exits with code 1.
- **Rollout success:** ✅ When all deployments succeed, exits with code 0.
- **Missing Secret:** ✅ Deploy stops with clear message and instructions to create Secret from example file.
- **Edge case:** Rollout timeout (120s) causes non-zero exit for that deployment, preventing silent deployment failures.

## Recommendations

1. **Install `shellcheck`** in the CI/CD environment for full lint validation
2. **Add `--dry-run` option** to build/push/transfer scripts for CI validation without side effects
3. **Consider adding retry logic** for SSH commands in unreliable network conditions

## Conclusion

All 5 automation scripts pass syntax validation and are safe for repeated execution. No hardcoded secrets, credentials, or runtime data were found.
