# GPU Runtime Validation

Date: 2026-07-19
Executor: hermes@vps2 (VPN 10.129.100.48)
Repository branch: aither-v2
Evidence collected at commit: 4b45879a2c4d
Corrective commit v1: be81b89
Corrective commit v2: aefd5e6
Corrective commit v3: (this commit)

## 1. Objective

Проверить, что Kubernetes видит GPU, NVIDIA device plugin работает, а Pod с лимитом `nvidia.com/gpu: 1` может выполнить `nvidia-smi`.

## 2. Evidence files

| Evidence | Path |
|---|---|
| NVIDIA pods | evidence/nvidia-pods.txt |
| RuntimeClass | evidence/runtimeclass.txt |
| GPU test pod describe | evidence/gpu-runtime-test-describe.txt |
| GPU test pod wide | evidence/gpu-runtime-test-pod-wide.txt |
| **nvidia-smi output** | **logs/gpu-runtime-test-nvidia-smi.log** |
| Events | evidence/aither-inference-events-tail.txt |

## 3. GPU allocatable

| Node | GPU allocatable | Evidence |
|---|---|---|
| n7 | 2 | evidence/describe-node-n7-gpu.txt |
| n8 | 1 | evidence/describe-node-n8-gpu.txt |

## 4. gpu-runtime-test result

| Check | Status | Evidence |
|---|---|---|
| Pod scheduled | PASSED | evidence/gpu-runtime-test-pod-wide.txt |
| Pod completed nvidia-smi | PASSED | logs/gpu-runtime-test-nvidia-smi.log |
| GPU visible inside container | PASSED | logs/gpu-runtime-test-nvidia-smi.log |
| No scheduling errors | PASSED | evidence/gpu-runtime-test-describe.txt |

### nvidia-smi output (full)

From `logs/gpu-runtime-test-nvidia-smi.log`:

```
Sun Jul 19 16:49:32 2026
NVIDIA-SMI 590.48.01
Driver Version: 590.48.01
CUDA Version: 13.1
GPU 0: Quadro RTX 6000 (Memory: 0MiB / 23040MiB, Utilization: 0%)
```

## 5. Conclusion

Status: PASSED

NVIDIA runtime fully operational. Container with `nvidia.com/gpu: 1` successfully executed `nvidia-smi` on n8 (control-plane). GPU Quadro RTX 6000 with driver **590.48.01** and CUDA **13.1** is visible and functional.

## 6. Failed / Partial items

| Item | Status | Reason | Required fix |
|---|---|---|---|
| — | PASSED | — | — |
