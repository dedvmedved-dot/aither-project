# FINAL DIAGNOSIS: Root cause confirmed

## Confirmed mechanism

```
containerd loses sandbox (reason TBD)
  → kubelet: PodSandboxStatus returns "not found"
  → kubelet: "Pod sandbox changed, it will be killed and re-created"
  → kubelet: StopContainer for static pod
  → containerd: SIGTERM (timeout from terminationGracePeriodSeconds)
  → if process doesn't exit in time: SIGKILL (exit 137)
```

## Evidence

### 1. SandboxChanged event (from kubelet logs)
```
Reason: SandboxChanged
Message: Pod sandbox changed, it will be killed and re-created.
Pod: etcd-bootsman-k8s-clnt01-n8-gpu
Count: 4 occurrences since 23:47 MSK
```

### 2. POD ID changes (both etcd and apiserver)
| Component | Old POD | New POD | Timeframe |
|---|---|---|---|
| apiserver | 846f65a6fce63 (NotReady) | 630ec0a67c3bd (Ready) | ~10 min ago |
| etcd | f981a42c264ff (NotReady) | 3902fe89780c2 (Ready) | ~10 min ago |

**Both sandboxes recreated simultaneously** → common containerd failure.

### 3. Containerd errors
Multiple `PodSandboxStatus for "..." failed: not found` errors logged by containerd.

### 4. Apiserver exit 137 chain (attempt #59)
```
23:53:19 — apiserver starts
23:54:23 — "Shutting down controller" (ALL controllers)
23:54:23 — "Stopped listening on [::]:6443"
23:54:53 — exit 137 (SIGKILL after 30s timeout)
```

## What we now know

1. **Kubelet is NOT the initiator** — it reacts to sandbox loss
2. **Containerd is the source** — sandboxes disappear from CRI
3. **Both etcd AND apiserver affected simultaneously** — rules out per-pod issue
4. **No manual kubelet restart needed** — cycle is self-sustaining

## Remaining question

**Why does containerd lose sandboxes?**

Candidates:
- containerd 1.7.28 bug or instability
- shim process crashes
- pause container exits
- CRI timeout/ttrpc errors
- resource pressure (unlikely: 736 GB RAM free)
- Astra-specific containerd integration issue

## Containerd state
- Version: 1.7.28 (below recommended 1.7.30 for CDI)
- NRestarts: 2
- Active since: 18:12 MSK (6+ hours ago)
- No astra-docker-isolation events found

## Next step

Monitor containerd events stream to catch the moment sandbox disappears:
```bash
ctr -n k8s.io events --no-resolve | tee -a /root/k8s-recovery/containerd-events.log
```
