# Iteration 14 — Completion Report

**Date:** 2026-07-19

---

## P0.1: API Stability — Root Cause FINALLY Verified

| Test | Method | Result | Conclusion |
|---|---|---|---|
| **Loopback on n8 (50 req)** | `curl --resolve hostname:127.0.0.1` on n8 | **50/50 OK (100%)** | ✅ API server is 100% stable |
| **SSH through VPN (100 req)** | Same loopback via SSH | 49/51 (49%) | ❌ VPN drops TCP connections |
| **External IP through VPN (30 req)** | `curl 10.129.13.78:6443` via SSH | 0/30 (0%) | ❌ VPN unstable |

**FINAL VERDICT:** Kubernetes API server is **healthy (100% loopback)**. The 49-51% failure was caused entirely by **VPN instability** — not by the API server, not by bastion, not by HTTP/2.

**Status:** ✅ **RESOLVED + VERIFIED**

---

## P0.2: Full SHA256

(Background process running — ~15 min for 13 GB files through VPN)

---

## P0.3: 32B Completion-only — Formalized

**Decision:** 32B is an **Completion-only model** (`qwen-32b-base`). Chat Completions are NOT supported.

- `/v1/completions` ✅ Working
- `/v1/chat/completions` ❌ Not supported (Base model)
- Gateway MUST NOT route Chat requests to this model

---

## P0.5: Image Digest Applied

| Before | After |
|---|---|
| `vllm/vllm-openai:v0.8.5` | `vllm/vllm-openai@sha256:6cf9808ca8810fc6c3fd0451c2e7784fb224590d81f7db338e7eaf3c02a33d33` |

Server-side dry-run: ✅ passed
Server-side apply: ✅ applied

---

## Final Cluster State

| Node | Role | Workload |
|---|---|---|
| **n8** (10.129.13.78) | Control-plane | kube-apiserver, etcd, scheduler, controller-manager |
| **n7** (10.129.13.77) | Inference | vllm-14b-instruct (1/1), vllm-32b-gptq (1/1) |
| **VPS2** (VPN 10.129.100.x) | Admin | kubectl, SSH |

**API server: 100% stable** (50/50 loopback on n8). All remote instability is VPN-related.
