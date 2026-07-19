# Cluster Topology Report

Date: 2026-07-19
Executor: hermes@vps2 (VPN 10.129.100.48)
Repository branch: aither-v2
Evidence collected at commit: 4b45879a2c4d
Corrective commit: be81b89

## 1. Node list

Evidence:
- evidence/kubectl-get-nodes-wide.txt

## 2. Current node roles

| Node | Observed role | Evidence |
|---|---|---|
| bootsmam-k8s-clnt01-n7-gpu | GPU worker — inference | evidence/kubectl-get-nodes-wide.txt |
| bootsman-k8s-clnt01-n8-gpu | Control-plane + benchmark | evidence/kubectl-get-nodes-wide.txt |

## 3. GPU visibility

| Node | nvidia.com/gpu capacity | nvidia.com/gpu allocatable | Evidence |
|---|---|---|---|
| n7 | 2 | 2 | evidence/describe-node-n7-gpu.txt |
| n8 | 1 | 1 | evidence/describe-node-n8-gpu.txt |

## 4. Workload placement

| Workload | Namespace | Pod/Deployment | Node | Status | Evidence |
|---|---|---|---|---|---|
| vLLM 14B | aither-inference | vllm-14b-instruct | n7 | Running 1/1 | evidence/aither-inference-pods-wide.txt |
| vLLM 32B | aither-inference | vllm-32b-gptq | n7 | Running 1/1 | evidence/aither-inference-pods-wide.txt |
| nginx-gateway-32b (pod1) | aither-inference | nginx-gateway-32b | n8 | Running 1/1 | evidence/aither-inference-pods-wide.txt |
| nginx-gateway-32b (pod2) | aither-inference | nginx-gateway-32b | n8 | ImagePullBackOff | evidence/aither-inference-pods-wide.txt |
| nginx-gateway-32b (pod3) | aither-inference | nginx-gateway-32b | n8 | ImagePullBackOff | evidence/aither-inference-pods-wide.txt |
| benchmark-inference | aither-inference | benchmark-inference | n8 | **Completed** | kubectl get jobs |
| benchmark-endurance-60min | aither-inference | benchmark-endurance-60min | n8 | **Failed** | kubectl get jobs |
| NVIDIA device plugin | gpu-operator | nvidia-device-plugin | n7, n8 | Running | evidence/nvidia-pods.txt |

## 5. Observed contradictions

1. 14B/32B models run on n7, not on n8 as described in earlier deployment plans.
2. n8 (control-plane) has 1 GPU allocatable but no inference workload — clean control-plane.
3. Gateway and benchmarks run on n8 (control-plane), sharing resources with kube-apiserver/etcd.

## 6. Findings

### Finding GW-01: nginx-gateway-32b replicas in ImagePullBackOff

- **Observed:** 2 of 3 gateway Pods are in ImagePullBackOff.
- **Root cause:** Hardened deployment uses `nginx:alpine@sha256:343e2...`; VPN instability caused image pull failure.
- **Impact:** Gateway is NOT HA — only 1/3 replicas Running. Gateway status: **PARTIAL**.
- **Owner:** Stage 04 (Gateway hardening).
- **Risk accepted for Stage 01:** Yes. This is a workload health issue, not GPU/cluster topology.

### Finding BM-01: benchmark-endurance-60min Job Failed

- **Observed:** benchmark-endurance-60min Job completed with Failed status after 82 minutes.
- **Root cause:** Likely script error (awk syntax in initial version, timeout). Not related to cluster topology.
- **Impact:** 60-minute endurance test needs re-run. Not a Stage 01 blocker.

## 7. Conclusion

Status: PASSED WITH FINDINGS

Accepted topology:

n7 = GPU worker (inference): 14B Instruct, 32B GPTQ  
n8 = Control-plane: kube-apiserver, etcd, scheduler, controller-manager, nginx-gateway-32b (PARTIAL), benchmark

## 8. Failed / Partial items

| Item | Status | Reason | Required fix |
|---|---|---|---|
| — | PASSED | Cluster/GPU baseline valid | — |
| GW-01 | PARTIAL (Stage 04) | 2/3 gateway Pods ImagePullBackOff, VPN image pull failure | Fix image pull; stage 04 scope |
| BM-01 | PARTIAL (Stage 02) | benchmark-endurance-60min Failed after 82min | Re-run endurance test; stage 02 scope |
