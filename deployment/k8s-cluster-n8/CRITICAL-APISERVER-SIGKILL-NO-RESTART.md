# CRITICAL FINDING: Apiserver crashes WITHOUT manual kubelet restart

## Discovery

**Apiserver attempt #59 crashed at 23:54 MSK with exit 137 (SIGKILL) — 8 minutes AFTER our last manual `systemctl restart kubelet`.**

This disproves the hypothesis that manual kubelet restarts are the sole cause.

## Evidence

| What | Value |
|---|---|
| Container ID | e63cd1f29cb67 |
| Exit code | **137 (SIGKILL)** |
| Started | 23:53:19 MSK |
| Finished | 23:54:53 MSK |
| Reason | Error |
| Kubelet PID | 740979 (new, started at 23:46:54, NOT restarted manually) |
| etcd status | **Healthy** (17ms) at time of crash |

## Crash sequence (from logs)

```
23:53:19 — apiserver starts (attempt 59)
23:54:23 — "Shutting down controller" (ALL controllers)
23:54:23 — "Stopped listening on [::]:6443"
23:54:53 — exit 137 (SIGKILL)
```

## What we ruled out

- ❌ Manual `systemctl restart kubelet` — was NOT performed
- ❌ etcd failure — etcd was healthy at crash time
- ❌ Two kubelet processes — old kubelet (PID 529815) died at 23:33, only new one running
- ❌ OOM — 736 GB free

## What remains unknown

**Why does kubelet issue StopContainer for apiserver?**

Possible chain:
```
etcd sandbox changes (attempt 49→50)
  → apiserver loses etcd connection
  → apiserver becomes unresponsive (but probes are removed!)
  → SOME TRIGGER causes kubelet to stop apiserver
  → StopContainer(timeout=30s)
  → apiserver doesn't shut down gracefully in 30s
  → SIGKILL (exit 137)
```

## Question for specialists

**What triggers kubelet to StopContainer for a static pod when liveness/readiness probes are removed?**

Without probes, what else can cause kubelet to decide "this static pod needs restarting"? Does kubelet monitor the pod's sandbox health? Does it react to etcd sandbox changes by restarting dependent static pods (apiserver, controller-manager, scheduler)?

Or is this a different mechanism — like `SyncLoop` detecting a manifest hash change, or `PLEG` (Pod Lifecycle Event Generator) detecting a container exit and triggering sandbox recreation for ALL static pods?
