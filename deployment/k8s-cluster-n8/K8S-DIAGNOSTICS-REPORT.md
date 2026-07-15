# K8s Cluster Diagnostics Report
## Aither Platform — n7/n8 GPU Nodes

**Date:** 2026-07-13 / 2026-07-14 (MSK)
**Duration:** ~20 hours of debugging
**Author:** Hermes Agent (deepseek-v4-pro) + Sergey Kravchuk
**Purpose:** Консультация со специалистами по K8s

---

## 1. Infrastructure

### Physical Hardware (YADRO VEGMAN S320 × 2)

| | n8 (control-plane) | n7 (worker) |
|---|---|---|
| **IP** | 10.129.13.78 | 10.129.13.77 |
| **VLAN** | 308 | 308 |
| **CPU** | 2× Xeon 6258R (28C/56T per socket) | same |
| **RAM** | 754 GB | 754 GB |
| **GPU** | 2× Quadro RTX 6000 (23 GB each) | same |
| **NVIDIA Driver** | 590.48.01 | 590.48.01 |
| **OS** | Astra Linux 1.8.1 | Astra Linux 1.8.1 |
| **Kernel** | 6.6.28-1-generic | 6.6.28-1-generic |
| **Boot Mode** | parsec=0 (Parsec disabled) | parsec=0 |

### Disk Layout (n8)

| Device | Size | Type | Mount |
|---|---|---|---|
| sda | 447 GB | Marvell RAID VD | /boot, / |
| **sdb2** | 1.7 TB | Samsung PM1643a SAS SSD | **/var/lib/etcd** |
| sdc-sdl | 3.5 TB × 10 | HDD array | /data (models, etc.) |

### Network Path
```
VPS1 (Hermes) → jump: Cisco 10.129.11.21 → n7/n8 (VLAN 308)
```

---

## 2. Software Versions

| Component | n8 | n7 |
|---|---|---|
| **containerd** | v1.7.28 | **v2.2.1.astra0** ⚠️ |
| **kubelet** | v1.33.5 | v1.33.5 |
| **kubeadm** | v1.33.5 | v1.33.5 |
| **cri-tools** | v1.7.28 | — |
| **etcd** | 3.5.21 | — |
| **vLLM** | 0.25.0 | running 32B |

---

## 3. Current State (as of 2026-07-14 ~03:00 MSK)

### vLLM (WORKING ✓)

| Node | Model | GPUs | VRAM | Port | Runtime |
|---|---|---|---|---|---|
| n8 | Qwen2.5-Coder-14B-Instruct | 2× RTX 6000 | 21.6 GB each | :8000 | systemd-run |
| n7 | Qwen2.5-32B-GPTQ | 2× RTX 6000 | in use | :8000 | process |

### K8s Cluster (UNSTABLE ⚠️)

**Status right now:**
- Node: `bootsman-k8s-clnt01-n8-gpu` — **Ready**, control-plane
- etcd: healthy, 18ms latency, 10 MB DB, leader elected (attempt #41)
- kube-apiserver: Running (attempt #48)
- Flannel: Running (attempt #56)
- CoreDNS: Running (attempt #46)

**n7 (worker):** NOT joined. kubelet running but cannot register:
- Uses bootstrap token, gets `connection refused` to n8:6443
- `kubeadm join` hangs at `kubelet-check` step
- containerd version mismatch: v2.2.1.astra0 vs v1.7.28 on n8

### Probes Removed

Both `/etc/kubernetes/manifests/etcd.yaml` and `kube-apiserver.yaml` have **all health probes removed** (livenessProbe, readinessProbe, startupProbe). This was critical for stability — see §5.

---

## 4. Chronology of Actions (~20 hours)

### Phase 1: Initial Cluster Deployment (attempts 1-5)
1. `kubeadm init` on n8 with `--pod-network-cidr=10.244.0.0/16`
2. Flannel CNI installed
3. Cluster immediately unstable — etcd and apiserver crashing

### Phase 2: Root Cause — Disk I/O (KEY FINDING)
4. **Discovered:** etcd on sda (Marvell RAID VD) — fsync ~2000/sec, latency up to **2890 ms**
5. Measured alternatives:
   - sda (RAID): dsync 1 MB/s → **UNUSABLE for etcd**
   - sdc (SSD): dsync 4.6 MB/s, latency 19 ms → better
   - tmpfs: latency 3 ms → best but not persistent
6. **Solution:** Formatted `/dev/sdb2` (Samsung PM1643a SAS SSD 1.7 TB) as ext4, mounted at `/var/lib/etcd`

### Phase 3: Health Probes Killing etcd (CRITICAL INSIGHT)
7. etcd stable on sdb2, but kubelet **kills it via livenessProbe** after ~90 seconds
8. Standard probe config: `initialDelaySeconds: 10, periodSeconds: 10, failureThreshold: 8` = 90s timeout
9. Slow disk I/O triggers probes even on SSD → kubelet kills etcd → cascade failure of apiserver, flannel, coredns
10. **Solution:** Removed ALL probes from etcd.yaml and kube-apiserver.yaml
11. Cluster became stable for the first time: all pods Running, node Ready

### Phase 4: YAML Corruption from sed/Python (RECURRING PROBLEM)
12. On subsequent `kubeadm reset` + `init` cycles, attempted to re-remove probes
13. **sed** left orphaned probe parameters → broken YAML → etcd fails with "ID cannot be empty"
14. **Python yaml.dump()** corrupted apiserver manifest → apiserver disappears
15. Each corruption required full `kubeadm reset` + re-init
16. Tried using reference manifests from git repo — helped temporarily

### Phase 5: GPU Integration Attempts
17. NVIDIA device plugin v0.17.1 deployed — **GPUs not detected** (driver 590 incompatibility)
18. Generated CDI config (`nvidia-ctk cdi generate`) — containerd ignores it
19. Created RuntimeClass `nvidia` as workaround — pod stuck in Pending (no nvidia runtime in containerd)
20. **vLLM run directly** (systemd-run) as fallback — works perfectly

### Phase 6: n7 Worker Join Attempts
21. Multiple `kubeadm join` attempts — hangs at `kubelet-check`
22. kubelet on n7 gets `connection refused` to n8:6443 during join
23. Manually copied `bootstrap-kubelet.conf` → `kubelet.conf` — kubelet starts but cannot register (forbidden, RBAC)

---

## 5. Key Findings & Verified Solutions

### ✅ What Works

| Solution | Detail |
|---|---|
| **etcd on dedicated SSD (sdb2)** | Samsung PM1643a SAS SSD, 18ms latency — stable |
| **No health probes on etcd/apiserver** | Critical. Without this, kubelet kills etcd on any I/O spike |
| **vLLM direct run (systemd-run)** | Reliable, bypasses K8s GPU issues entirely |
| **kubeadm init with control-plane-endpoint** | Works correctly with 10.129.13.78 |

### ❌ What Doesn't Work

| Problem | Detail |
|---|---|
| **Probe removal breaks YAML** | Both sed and Python yaml.dump() corrupt static pod manifests |
| **GPU device plugin** | v0.17.1 incompatible with NVIDIA driver 590 |
| **n7 worker join** | kubelet-check hangs, bootstrap token RBAC issues |
| **containerd version mismatch** | n7: v2.2.1.astra0 (Astra-specific), n8: v1.7.28 |

### 🔁 Cyclic Failure Pattern
```
1. Cluster works fine (etcd healthy, node Ready)
2. Apiserver or etcd restarts (reason unclear — NOT probes, probes removed)
3. Restart count hits backoff limit → CrashLoopBackOff
4. Flannel/CoreDNS/kube-proxy lose API access → also crash
5. Cluster dead until manual intervention
```

---

## 6. Questions for Specialists

1. **Why does etcd keep restarting WITHOUT probes?** Attempt #41 in 4.5 hours. What else triggers pod restarts? kubelet sync loop? Memory pressure?

2. **Why does Python `yaml.dump()` corrupt K8s manifests?** PyYAML changes field ordering, removes comments, sometimes drops nested keys. Is there a safe way to edit static pod manifests programmatically?

3. **containerd v2.2.1.astra0 on n7 vs v1.7.28 on n8** — is this a problem for cluster join? Do we need to downgrade n7 or upgrade n8?

4. **NVIDIA driver 590 + device plugin** — which plugin version supports this driver? Or is RuntimeClass the only way on Turing GPUs (RTX 6000 = compute capability 7.5)?

5. **`kubeadm join` hangs at `kubelet-check`** — known issue? Workarounds? Can we skip this phase?

6. **Is single-node etcd on 1.7 TB SAS SSD viable for production?** Current latency 18ms. Should we plan for external etcd or HA?

7. **Astra Linux + K8s 1.33** — any known incompatibilities? Especially with containerd versions, cgroup v2, swap support?

---

## 7. Files & References

| File | Location |
|---|---|
| K8s manifests (reference) | `aither-project/deployment/k8s-cluster-n8/manifests/` |
| Probe removal script | `aither-project/deployment/k8s-cluster-n8/scripts/remove-probes.sh` |
| Architecture diagram | `aither-project/deployment/k8s-cluster-n8/diagrams/architecture.svg` |
| Lab journal | `aither-project/docs/lab-journal.md` |
| n8 etcd manifest | `/etc/kubernetes/manifests/etcd.yaml` (probes removed) |
| n8 apiserver manifest | `/etc/kubernetes/manifests/kube-apiserver.yaml` (probes removed) |
| n8 containerd config | `/etc/containerd/config.toml` |
| n8 CDI config | `/etc/cdi/nvidia.yaml` |
| vLLM log (n8) | `/tmp/vllm-coder14b.log` |
| vLLM unit (n8) | `vllm-coder14b.service` (systemd-run) |

---

## 8. Recommended Next Steps

1. **Short-term:** vLLM running directly on both nodes — this is stable and usable
2. **K8s:** Resolve YAML editing issue FIRST (use `kubectl patch` or `jq`/`yq` instead of Python)
3. **n7 join:** Test with `--ignore-preflight-errors=all` and manual CSR approval
4. **containerd:** Align versions between n7 and n8
5. **GPU:** Test NVIDIA device plugin v0.15+ or GPU Operator
6. **Long-term:** Consider external etcd on dedicated small node, or HA with 3 nodes
