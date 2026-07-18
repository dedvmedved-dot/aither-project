# n7 Forensic Results — Root cause found

**Date:** 2026-07-19
**Node:** bootsmam-k8s-clnt01-n7-gpu (10.129.13.77)

---

## Root Cause

**A systemd unit `/etc/systemd/system/vllm-32b.service` was running vLLM directly on the host** with `tensor-parallel-size=2`, outside of Kubernetes. This service:

- Started vLLM Qwen2.5-32B-GPTQ with TP=2 at **01:32:46** (before any of the 5 test cycles)
- Occupied **21.65 GiB VRAM** per process (both GPUs: all 48 GB)
- Its processes PID 1137814 (VLLM::Worker_TP0) and 1137815 (VLLM::Worker_TP1) were in cgroup `/system.slice/vllm-32b.service` (NOT in `kubepods.slice/...`)
- PPID was systemd, NOT containerd-shim
- Were in host PID namespace (pid:[4026531836])
- Persisted across all 5 Kubernetes pod deletion cycles because systemd restarts them on kill

## Why the original n7 recovery test was invalid

| Observation | Explanation |
|---|---|
| Same PIDs 1137814/1137815 across 5 cycles | NOT Kubernetes pod processes — they were from the systemd unit |
| Named `VLLM::Worker_TP0` and `VLLM::Worker_TP1` while K8s deployment has `tensor-parallel-size=1` | Systemd unit had `--tensor-parallel-size 2` |
| GPU never freed between cycles | Processes were owned by systemd, not the deleted pods |
| Cycle 5 CrashLoopBackOff (CUDA OOM) | K8s pod tried to allocate model but systemd vLLM held 44+ GiB VRAM |

## Current State

| Item | Status |
|---|---|
| PID 1137814/1137815 | ✅ **KILLED** (SIGKILL via `systemctl kill -s KILL`) |
| vllm-32b.service | ✅ **Disabled** (`systemctl disable`) |
| GPU 0 memory | ✅ **Free** (22.5 GiB available) |
| GPU 1 memory | ✅ **Free** (22.5 GiB available) |
| GPU processes | ✅ **Zero** |
| n7 node | ✅ **Cordoned** (will stay until 5 clean cycles) |
| 32B Pod | ✅ **Running on n8** with 0 restarts |
| 32B Completion test | ✅ **Working** ("Paris. Yes, that's correct...") |

## What was learned

1. The original "orphan problem" was NOT a containerd/kubelet bug — it was a stale systemd service occupying GPU memory
2. The n7 recovery test methodology was flawed: `--now` deletion + fast reschedule made it impossible to distinguish pod processes from systemd processes
3. All symptoms (persistent PIDs, TP0+TP1 with TP=1 deployment, CrashLoopBackOff from CUDA OOM) are explained by this single root cause
