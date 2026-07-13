# Final Report: Root Cause + Monitoring Data

## Summary for Specialists

**Root cause confirmed:** containerd loses pod sandboxes → kubelet detects `SandboxChanged` → `StopContainer` → `SIGTERM` → if graceful shutdown exceeds timeout → `SIGKILL` (exit 137).

**Key evidence:**
1. Kubelet log: `Reason: SandboxChanged, Message: Pod sandbox changed, it will be killed and re-created` (4 occurrences)
2. Both etcd AND apiserver sandboxes recreated simultaneously (same timestamp)
3. Containerd events stream shows multiple `exit_status:137` events
4. Cycle self-sustaining: no manual kubelet restart needed

**Monitoring results (10 minutes):**
- etcd: attempt 53 → 57 (4 restarts)
- apiserver: attempt 62 → 64 (2 restarts)
- Watchdog: livez=ok, readyz=ok throughout (fast recovery between 30s checks)
- Containerd events: 227 lines, multiple `exit_status:137`

**Remaining question:**
Why does containerd 1.7.28 lose sandboxes on Astra Linux 1.8.1?

## Files

| File | Contents |
|---|---|
| `FINAL-DIAGNOSIS-SANDBOX.md` | Full diagnosis with evidence chain |
| `full-report.txt` (659 lines) | Watchdog + containerd events + current state |
| `watchdog-k8s.log` | livez/readyz/etcd health every 30s |
| `containerd-events.log` | `ctr events` stream — raw sandbox lifecycle |

## Environment

- n8: Astra Linux 1.8.1, kernel 6.6.28, containerd 1.7.28, K8s 1.33.5
- n7: Astra Linux 1.8.1, containerd 2.2.1.astra0 (worker, stable)
- etcd on Samsung PM1643a SAS SSD (sdb2)
- NVIDIA driver 590 (package removed, kernel module active)
- parsec=0, health probes removed from static pod manifests
- `terminationGracePeriodSeconds: 300` (etcd), default 30s (apiserver)
