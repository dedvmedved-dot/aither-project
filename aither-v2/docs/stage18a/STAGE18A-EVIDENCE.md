# Stage 18A — Evidence Summary

## Deliverables

### Artifact Delivery (Stage 18E)

| Item | Method | Result |
|---|---|---|
| Source archive transfer | rsync --partial --append-verify | ✅ PASS (609 KB, 1 connection) |
| Identity image | rsync + zstd (53 MB) | ✅ PASS (~18 resume connections) |
| Portal Backend image | rsync + zstd (53 MB) | ✅ PASS (~15 resume connections) |
| AI Platform image | rsync + zstd (53 MB) | ✅ PASS (~20 resume connections) |
| Image import on n8 | `ctr images import` | ✅ PASS |
| Push to persistent registry | `ctr images push --plain-http` | ✅ PASS (122.7 MiB/s localhost) |

### Registry Persistence (Stage 18E Gate)

| Test | Result |
|---|---|
| Registry API `/v2/` | ✅ 200 OK |
| Catalog after push | ✅ 3 repositories |
| Tags verified | ✅ `stage18a-82fe433` |
| Registry restart test | ✅ Catalog preserved |
| Containerd restart test | ✅ Catalog preserved (systemd dependency chain) |
| Storage verified | ✅ `/var/lib/aither-registry/docker/registry/v2` (bind-mount) |

### CRI Recovery (Stage 18H)

| Test | Result |
|---|---|
| CRI plugins after fix | ✅ All ok |
| `crictl info` | ✅ RuntimeReady=true, NetworkReady=true |
| kubelet restart | ✅ active |
| Node Ready | ✅ `bootsman-k8s-clnt01-n8-gpu` Ready |
| Registry after recovery | ✅ All 3 repositories intact |
| Root cause | Configuration conflict (mirrors + config_path) |

### Runtime Deployment (Stage 18I)

| Step | Result |
|---|---|
| n7 containerd config | ✅ hosts.toml created |
| n7 node status | ✅ Ready |
| n8 node status | ✅ Ready |
| Manifest tag update | ✅ stage15→stage18a-82fe433 |
| Dry run | ✅ All 3 manifests valid |
| Rollout | ✅ identity, portal-backend, ai-platform |
| Pods Running | ✅ All 3/3 on n8 |
| Image ID verification | ✅ SHA-256 matches expected digests |
| Health checks | ✅ All services respond 200 |

### Images

| Image | Tag | Digest |
|---|---|---|
| aither-identity | `stage18a-82fe433` | `sha256:427314f4294323dba9c445f21aedffa49133a0e516a3188e9707f2b5a7a69b93` |
| aither-portal-backend | `stage18a-82fe433` | `sha256:940bc63a2e5906d0a5fb36063135a4bf6591d5642bd3aaf008740a4f6b18c76a` |
| aither-ai-platform | `stage18a-82fe433` | `sha256:ab2825fcefaa7363b124edc1f8d644f7d551087eea2d6572e03bddc099c8961f` |

## Stage 18J — Pre-Commit Validation Results

### n7 Image Pull Verification

A temporary test pod (`stage18a-test-pull`) was created on n7 using `nodeName: bootsmam-k8s-clnt01-n7-gpu`, running `aither-identity:stage18a-82fe433` with `command: ["python3", "-c", "import sqlite3; print('OK: crictl pull + startup verified'); open('/data/test_write','w').write('ok'); print('OK: writable /data')"]`.

**Result:** ✅ Pod completed successfully on n7
- `OK: crictl pull + startup verified`
- `OK: writable /data` (emptyDir)

**Note:** Initial pull failed with `https://... http: server gave HTTP response to HTTPS client` because n7 used default `config_path = '/etc/containerd/certs.d:/etc/docker/certs.d'` (colon-separated). Fixed by setting `config_path = '/etc/containerd/certs.d'` (single path), then restarting containerd + kubelet on n7.

### Scheduler Analysis

**Classification:** B + D — Scheduler works correctly. Pods run on n8 (control-plane) because old Stage 15-16 deployments were created with `nodeName: bootsman-k8s-clnt01-n8-gpu`. When Stage 18A manifests (without `nodeName`) were applied via `kubectl apply`, the live `nodeName` field persisted in the pod template. Kubernetes scheduler is not involved — `nodeName` bypasses scheduling entirely.

Both nodes have no taints. n7 is schedulable (`Unschedulable: false`, `Taints: <none>`). A test pod with explicit `nodeName: n7` ran successfully.

**Recommendation:** To distribute pods across both nodes, remove `nodeName` from live objects via `kubectl patch deployment ... -p '{"spec":{"template":{"spec":{"nodeName":null}}}}'` before next deployment.

### Portal-Backend Verification

**Classification:** B — Timeout reproduced, root cause documented as **API connectivity issue**, not service issue.

- Service: `ClusterIP 10.100.101.65:8000` → `targetPort: 8000`
- Endpoints: `10.244.0.237:8000` (pod on n8)
- Pod logs confirm `200 OK` responses to liveness/readiness probes:
  ```
  "GET /ready HTTP/1.1" 200 OK
  "GET /health HTTP/1.1" 200 OK
  ```
- Port-forward from build host timed out due to intermittent API server connectivity (`dial tcp 10.129.13.78:6443: i/o timeout`), which is a known build-host-to-cluster issue.

Portal-backend is fully functional — kubelet probes pass consistently (pod Running 1/1, 0 restarts).

### CrashLoopBackOff Classification

| Pod | Namespace | Image Tag | Stage18A? | Notes |
|---|---|---|---|---|
| `node-debugger-bootsmam-k8s-clnt01-n7-gpu-lt882` | default | N/A | ❌ | Pre-existing debug pod, Error since creation, unrelated to Aither |

No other CrashLoopBackOff pods exist. All Stage 18A pods are Running 1/1 on n8.
