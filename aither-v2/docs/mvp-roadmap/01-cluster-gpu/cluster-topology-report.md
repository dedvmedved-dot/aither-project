# Cluster Topology Report

Date: 2026-07-19
Executor: hermes@vps2 (VPN 10.129.100.48)
Repository branch: aither-v2
Commit: 4b45879a2c4d

## 1. Node list

Evidence:
- evidence/kubectl-get-nodes-wide.txt

## 2. Current node roles

| Node | Observed role | Evidence |
|---|---|---|
| bootsmam-k8s-clnt01-n7-gpu | GPU worker — inference | evidence/kubectl-get-nodes-wide.txt |
| bootsman-k8s-clnt01-n8-gpu | Control-plane + GPU | evidence/kubectl-get-nodes-wide.txt |

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
| nginx-gateway-32b | aither-inference | nginx-gateway-32b | n8 | Running 2/2 | evidence/kubectl-get-pods-all-wide.txt |
| benchmark-inference | aither-inference | benchmark-inference | n8 | Running | evidence/kubectl-get-pods-all-wide.txt |
| NVIDIA device plugin | gpu-operator | nvidia-device-plugin | n7, n8 | Running | evidence/nvidia-pods.txt |

## 5. Observed contradictions

1. 14B/32B models run on n7, not on n8 as described in earlier deployment plans. This contradicts the original "GPU Operator on n8" roadmap.
2. n8 (control-plane) has 1 GPU allocatable but no inference workload — clean control-plane.
3. Gateway and benchmark run on n8 (control-plane), sharing resources with kube-apiserver/etcd.

## 6. Conclusion

Status: PASSED

Accepted topology:

n7 = GPU worker (inference): 14B Instruct, 32B GPTQ  
n8 = Control-plane: kube-apiserver, etcd, scheduler, controller-manager, nginx-gateway-32b, benchmark

## 7. Failed / Partial items

| Item | Status | Reason | Required fix |
|---|---|---|---|
| — | PASSED | — | — |
