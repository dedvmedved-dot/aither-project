# Stage 18A — Final Report (Historical Pre-Commit Snapshot)

> **NOTE:** This document is a historical snapshot of the Stage 18A pre-commit
> state (HEAD `82fe433`). It describes the state *before* the Stage 18A commit
> was created and pushed. For current state after commit `ac74963`, refer to
> the git log or run `git show --stat HEAD`.

## A. Repository State (Snapshot — Pre-Commit)

| Field | Value |
|-------|-------|
| Repository | `dedvmedved-dot/aither-project` |
| Branch | `aither-v2` |
| HEAD (at snapshot) | `82fe433845f8487296033e80e249160b8f7a58d7` |
| Working directory | `/root/aither-v2/aither-v2/` |

## B. Summary

Stage 18A pre-commit preparation complete. All changes have been verified:

- **Persistent registry** (`registry:2` on n8:5000) — operational with 3 Stage 18A images
- **containerd CRI** — recovered from `config_path`/`mirrors` conflict (Stage 18H), both nodes healthy
- **Stage 18A services** — 3 microservices (identity, portal-backend, ai-platform) deployed, Running 1/1, health checks pass
- **Non-root security** — All Dockerfiles updated with `COPY --chown=1000:1000` and `USER 1000`
- **Automation scripts** — 5 scripts (build, transfer, push, verify, deploy) — all pass syntax check
- **Documentation** — 6 core docs + 5 final reports — no contradictions
- **Pre-commit manifest** prepared with complete file inventory

## C. Planned Commit Scope

**Modified files (6):**
1. `services/identity/Dockerfile` — non-root user security fix
2. `services/identity/k8s/identity.yaml` — image tag `:stage15` → `:stage18a-82fe433`
3. `services/portal-backend/Dockerfile` — non-root user security fix
4. `services/portal-backend/k8s/portal-backend.yaml` — image tag `:stage15` → `:stage18a-82fe433`
5. `services/ai-platform/Dockerfile` — non-root user security fix
6. `services/ai-platform/k8s/ai-platform.yaml` — image tag `:stage16` → `:stage18a-82fe433`

**New files (16):**
7–11. `scripts/stage18a-{build-images,transfer-artifact,push-images,verify-registry,deploy-services}.sh`
12–17. `docs/stage18a/{ARCHITECTURE,REGISTRY,DEPLOYMENT,RUNTIME-EVIDENCE,N8-CRI-RECOVERY,STAGE18A-EVIDENCE}.md`
18–22. `docs/stage18a/{stage18a-pre-commit-manifest,stage18a-regression-summary,stage18a-security-scan,stage18a-automation-validation,stage18a-evidence-index}.md`

**Total: 22 files (6 modified + 16 new)**

## D. Excluded Files

All scripts and files not related to Stage 18A (test scripts for Stage 15/16/17, bootstrap-admin.sh, check-gateway-32b.sh, etc.) are excluded.

## E. Validation Results

| Check | Result |
|-------|--------|
| `git diff --check` | ✅ CLEAN |
| Secret scan | ✅ CLEAN — no real secrets in Stage 18A scope |
| Large-file scan (>5MB) | ✅ CLEAN — none found |
| Binary/archive scan | ✅ CLEAN — none found |
| Automation syntax (`bash -n`) | ✅ ALL 5 SCRIPTS PASS |
| Automation lint (`shellcheck`) | ⚠️ NOT RUN — TOOL NOT INSTALLED |
| Regression (14 tests) | ✅ 14/14 PASS |
| Documentation consistency | ✅ REVIEWED — no contradictions after ARCHITECTURE.md/REGISTRY.md update |

## F. Stage 18A Infrastructure State

| Component | Status |
|-----------|--------|
| **Node 1** (`bootsmam-k8s-clnt01-n7-gpu`) | ✅ Ready (Worker, containerd://2.2.1) |
| **Node 2** (`bootsman-k8s-clnt01-n8-gpu`) | ✅ Ready (Control Plane, containerd://2.2.1) |
| **containerd** | ✅ active on both nodes, `config_path` scheme verified |
| **CRI** | ✅ RuntimeReady=true, NetworkReady=true, all plugins ok |
| **Registry** (`10.129.13.78:5000`) | ✅ Active, 3 repositories, persistent storage |
| **Stage 18A image pull** | ✅ n8 (`crictl pull` — up to date), n7 (kubelet CRI pull via test pod — verified) |
| **Rollout** | ✅ All 3 deployments successfully rolled out |
| **Health checks** | ✅ identity 200 OK (port-forward), portal-backend 200 OK (kubelet probes), ai-platform 200 OK (kubelet probes) |

## G. Evidence Index

All evidence files are located in `docs/stage18a/`:

| File | Description |
|------|-------------|
| `ARCHITECTURE.md` | Architecture overview |
| `REGISTRY.md` | Registry configuration |
| `DEPLOYMENT.md` | Deployment guide |
| `RUNTIME-EVIDENCE.md` | Pod/node/CRI/health status |
| `N8-CRI-RECOVERY.md` | CRI recovery diagnosis and fix |
| `STAGE18A-EVIDENCE.md` | Comprehensive evidence summary |
| `stage18a-pre-commit-manifest.md` | Pre-commit manifest |
| `stage18a-regression-summary.md` | Regression test results |
| `stage18a-security-scan.md` | Security scan |
| `stage18a-automation-validation.md` | Automation scripts validation |
| `stage18a-evidence-index.md` | Evidence index |

## H. Risks and Limitations (Snapshot)

1. **n7 `crictl` not installed** — kubelet pulls images via CRI correctly; manual `crictl pull` unavailable on n7
2. **Stage 18A pods pinned to n8** — historical `nodeName` from Stage 15-16 persists in live Deployment objects. Requires `kubectl patch` to enable multi-node scheduling
3. **Portal-backend port-forward timeout from build host** — not a service defect (kubelet confirms 200 OK). Root cause: intermittent K8s API connectivity from build host
4. **Registry without TLS** — Acceptable for cluster-internal deployment. Need TLS if exposed externally
5. **Registry without auth** — Open for read/write on cluster network. Documented limitation
6. **`REPLACE_ME` placeholder** — moved to `identity-secret.example.yaml` in C1 corrective actions; deployment will fail if Secret missing
7. **Pre-existing `node-debugger` pod in Error state** — unrelated to Stage 18A, in `default` namespace

## I. Proposed Commit Message

```
stage18a: implement persistent registry and containerd CRI recovery

- Add persistent container registry (registry:2) on control-plane node
- Fix containerd CRI: replace legacy mirrors/config_path conflict with config_path scheme
- Add non-root user (UID 1000) to service Dockerfiles
- Update all service manifests to use stage18a-82fe433 images from private registry
- Add automation scripts: build, transfer, push, verify, deploy
- Add comprehensive documentation: architecture, registry, deployment, CRI recovery, evidence
- Verify: both nodes Ready, CRI operational, all services Running, health checks passing
```
