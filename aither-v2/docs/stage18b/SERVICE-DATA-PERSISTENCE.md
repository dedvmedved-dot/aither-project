# Stage 18B — Service Data Persistence

## Persistent Storage Topology

| Layer | Identity | AI Platform |
|-------|----------|-------------|
| **Deployment** | `aither-identity` | `aither-ai-platform` |
| **Volume mount** | `/data` | `/data` |
| **PVC** | `aither-identity-data` | `aither-ai-platform-data` |
| **PV** | `pv-aither-identity-data` | `pv-aither-ai-platform-data` |
| **Access mode** | ReadWriteOnce | ReadWriteOnce |
| **Reclaim policy** | Retain | Retain |
| **Capacity** | 1Gi | 1Gi |

**Stateless services:** aither-portal-backend (no PVC — persistence not applicable)

---

## Historical Marker Clarification

Three marker tests were conducted across Stage 18B and corrective stages:

| Marker | Service | Stage | Purpose | Pod deleted | Result |
|--------|---------|-------|---------|-------------|--------|
| `stage18b-persistence-marker-1784738828` | aither-identity | Stage 18B (original) | Initial identity PVC persistence verification | ✅ identity `-2rkgq` → `-c7r2h` | ✅ preserved |
| `stage18b-c1-marker-1784740580` | aither-identity | Stage 18B-C1 | Corrective re-verification of identity PVC | ✅ identity `-278cv` → `-vk7pm` | ✅ preserved |
| `stage18b-c3-ai-platform-marker-1784743322` | aither-ai-platform | Stage 18B-C3 | AI Platform PVC persistence verification | ✅ ai-platform `-gxjcm` → `-bfgqn` | ✅ preserved |

**Explanation:** The three markers represent three separate test runs, each with its own timestamp. The first two were both on identity service (Stage 18B original and Stage 18B-C1 re-verification). The third is the AI Platform corrective test added in Stage 18B-C3. There is no data conflict — each test is independently documented with its own timestamp and pod lifecycle.

---

## Stage 18B Original — Identity Persistence Test

### Marker

| Field | Value |
|-------|-------|
| Marker | `stage18b-persistence-marker-1784738828` |
| Path | `/data/stage18b-marker.txt` |
| Service | aither-identity |
| PVC | `aither-identity-data` |
| PV | `pv-aither-identity-data` (Retain policy) |

### Procedure

1. Write marker to PVC: `echo 'stage18b-persistence-marker-1784738828' > /data/stage18b-marker.txt`
2. Verify marker content via `crictl exec`
3. Delete pod: `kubectl delete pod -l app=aither-identity`
4. Wait for new pod creation and readiness
5. Verify marker content in new pod via `crictl exec`

### Result

| Step | Outcome |
|------|---------|
| Marker created | ✅ `stage18b-persistence-marker-1784738828` |
| Pod deleted | ✅ identity-79cbf4c96d-2rkgq → identity-79cbf4c96d-c7r2h |
| New pod Running | ✅ 1/1 |
| Marker preserved after pod recovery | ✅ `stage18b-persistence-marker-1784738828` |
| PVC/PV binding unchanged | ✅ Both `Bound` |

---

## Stage 18B-C3 — AI Platform Corrective Persistence Test

### Corrective marker

| Field | Value |
|-------|-------|
| Marker | `stage18b-c3-ai-platform-marker-1784743322` |
| File path | `/data/stage18b-c3-marker.txt` |
| Service | aither-ai-platform |
| PVC | `aither-ai-platform-data` |
| PV | `pv-aither-ai-platform-data` (Retain policy) |
| Mount path verified | ✅ `/data` — `/dev/mapper/...` ext4 on n8 |

### Deleted pod identity

| Field | Value |
|-------|-------|
| Deleted pod | `aither-ai-platform-d6fc574cf-gxjcm` |
| Deleted pod UID | `c5946712-75c1-49a2-b00c-665138989c41` |
| Deletion command | `kubectl delete pod aither-ai-platform-d6fc574cf-gxjcm -n aither-inference --wait=true` |
| Deletion exit code | 0 |
| Timestamp | 2026-07-22T18:02:19Z |

### Replacement pod identity

| Field | Value |
|-------|-------|
| Replacement pod | `aither-ai-platform-d6fc574cf-bfgqn` |
| Replacement pod UID | `17969774-d49c-46fe-8224-ff3e0579a90b` |
| Node | `bootsman-k8s-clnt01-n8-gpu` |
| Phase | `Running` |
| Container ready | `true` |
| Restart count | 0 |
| Rollout status | 1 ready, 1 available, 1 desired (k8s API intermittent — `rollout status` timed out, pod verified Running via `kubectl get pods` and `crictl`) |
| Rollout exit code | N/A (API timeout — pod verified Running) |

### Marker verification after replacement

| Field | Value |
|-------|-------|
| Command | `kubectl exec -n aither-inference <replacement-pod> -- cat /data/stage18b-c3-marker.txt` |
| Read exit code | 0 |
| Expected marker | `stage18b-c3-ai-platform-marker-1784743322` |
| Actual marker | `stage18b-c3-ai-platform-marker-1784743322` |
| **Verdict** | ✅ **PASS — marker preserved** |

### Health ×3 after recovery

| Attempt | Timestamp | HTTP Status |
|---------|-----------|-------------|
| 1 | 2026-07-22T18:04:08Z | 200 |
| 2 | 2026-07-22T18:04:09Z | 200 |
| 3 | 2026-07-22T18:04:10Z | 200 |

### PVC/PV status before and after

| Resource | Before | After | Status |
|----------|--------|-------|--------|
| PVC `aither-ai-platform-data` | Bound | Bound | ✅ unchanged |
| PV `pv-aither-ai-platform-data` | Bound | Bound | ✅ unchanged |
| Reclaim policy | Retain | Retain | ✅ unchanged |

---

## Conclusion

**Tested persistence:** aither-identity (×2), aither-ai-platform (×1)
**Not applicable (stateless):** aither-portal-backend
**Overall verdict:** ✅ Persistent data survives pod recreation on all tested services. PVC/PV bindings with `Retain` reclaim policy ensure data integrity across pod lifecycle events.
