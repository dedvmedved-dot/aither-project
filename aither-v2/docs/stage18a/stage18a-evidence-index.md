# Stage 18A — Evidence Index

## Evidence Files

| ID | File | Type | Description | Contains Runtime Data | Contains Secrets |
|----|------|------|-------------|----------------------|------------------|
| E-01 | `docs/stage18a/ARCHITECTURE.md` | Documentation | Architecture overview (nodes, services, registry, containerd config) | ✅ Node IPs, registry URL | ❌ No secrets |
| E-02 | `docs/stage18a/REGISTRY.md` | Documentation | Registry setup (systemd unit, API, images, hosts.toml) | ✅ Registry URL, image tags | ❌ No secrets |
| E-03 | `docs/stage18a/DEPLOYMENT.md` | Documentation | Deployment guide, rollback, PV/PVC recovery | ❌ Commands only | ❌ No secrets |
| E-04 | `docs/stage18a/RUNTIME-EVIDENCE.md` | Evidence | Pod/node status, CRI status, health check results | ✅ Pod IPs, image IDs, timestamps | ❌ No secrets |
| E-05 | `docs/stage18a/N8-CRI-RECOVERY.md` | Evidence | CRI recovery diagnosis, fix, verification | ✅ Config diffs, plugin status | ❌ No secrets |
| E-06 | `docs/stage18a/STAGE18A-EVIDENCE.md` | Evidence | Comprehensive evidence (Stage 18E→J), images, scheduler, portal-backend | ✅ Image digests, pod status | ❌ No secrets |
| E-07 | `docs/stage18a/stage18a-pre-commit-manifest.md` | Report | Pre-commit manifest with validation results | ❌ No runtime data | ❌ No secrets |
| E-08 | `docs/stage18a/stage18a-regression-summary.md` | Report | Regression test results (14/14 PASS) | ❌ No runtime data | ❌ No secrets |
| E-09 | `docs/stage18a/stage18a-security-scan.md` | Report | Security scan report (no critical findings) | ❌ No runtime data | ❌ No secrets |
| E-10 | `docs/stage18a/stage18a-automation-validation.md` | Report | Automation scripts validation (all pass) | ❌ No runtime data | ❌ No secrets |
| E-11 | `docs/stage18a/stage18a-evidence-index.md` | Report | This file — evidence index | ❌ No runtime data | ❌ No secrets |

## Stage 18A Images

| Image | Registry Path | Tag | SHA-256 Digest | Used by Workload | Pull Verified |
|-------|--------------|-----|---------------|-----------------|---------------|
| aither-identity | `10.129.13.78:5000/aither-identity` | `stage18a-82fe433` | `sha256:427314f4294323dba9c445f21aedffa49133a0e516a3188e9707f2b5a7a69b93` | ✅ Pod `aither-identity-79cbf4c96d-xbr99` | ✅ n8 (`crictl pull` — up to date), n7 (kubelet pull via test pod — verified) |
| aither-portal-backend | `10.129.13.78:5000/aither-portal-backend` | `stage18a-82fe433` | `sha256:940bc63a2e5906d0a5fb36063135a4bf6591d5642bd3aaf008740a4f6b18c76a` | ✅ Pod `aither-portal-backend-f44cfcbbc-ck8jz` | ✅ n8 (`crictl pull` — up to date) |
| aither-ai-platform | `10.129.13.78:5000/aither-ai-platform` | `stage18a-82fe433` | `sha256:ab2825fcefaa7363b124edc1f8d644f7d551087eea2d6572e03bddc099c8961f` | ✅ Pod `aither-ai-platform-d6fc574cf-gxjcm` | ✅ n8 (`crictl pull` — up to date) |

## Live System Evidence (2026-07-22)

| Check | Result | Source |
|-------|--------|--------|
| Both nodes Ready | ✅ n7 Ready, n8 Ready | `kubectl get nodes` |
| containerd (n8) | ✅ active | `systemctl is-active containerd` via SSH |
| kubelet (n8) | ✅ active | `systemctl is-active kubelet` via SSH |
| aither-registry (n8) | ✅ active | `systemctl is-active aither-registry` via SSH |
| Registry API /v2/ | ✅ `{}` 200 OK | `curl localhost:5000/v2/` via SSH |
| Registry catalog | ✅ 3 repositories | `curl localhost:5000/v2/_catalog` via SSH |
| CRI RuntimeReady | ✅ true | `crictl info` via SSH |
| CRI NetworkReady | ✅ true | `crictl info` via SSH |
| Identity rollout | ✅ successfully rolled out | `kubectl rollout status` |
| Portal-backend rollout | ✅ successfully rolled out | `kubectl rollout status` |
| AI Platform rollout | ✅ successfully rolled out | `kubectl rollout status` |
| Identity pod Ready | ✅ 1/1, Running 0 restarts | `kubectl describe pod` |
| Portal-backend pod Ready | ✅ 1/1, Running 0 restarts | `kubectl describe pod` |
| AI Platform pod Ready | ✅ 1/1, Running 0 restarts | `kubectl describe pod` |
| Identity Image ID | ✅ SHA-256 matches | `kubectl describe pod` |
| Portal-backend Image ID | ✅ SHA-256 matches | `kubectl describe pod` |
| AI Platform Image ID | ✅ SHA-256 matches | `kubectl describe pod` |
| containerd version | ✅ 2.2.1.astra0 | `ctr version` via SSH |
| Git diff --check | ✅ CLEAN | `git diff --check` |
| Git staged area | ✅ EMPTY (no staged changes) | `git diff --cached --stat` |
