# GPU Runtime Validation

Date: 2026-07-19
Executor: hermes@vps2 (VPN 10.129.100.48)
Repository branch: aither-v2
Commit: 4b45879a2c4d

## 1. Objective

Проверить, что Kubernetes видит GPU, NVIDIA device plugin работает, а Pod с лимитом `nvidia.com/gpu: 1` может выполнить `nvidia-smi`.

## 2. Evidence files

| Evidence | Path |
|---|---|
| NVIDIA pods | evidence/nvidia-pods.txt |
| RuntimeClass | evidence/runtimeclass.txt |
| GPU test pod describe | evidence/gpu-runtime-test-describe.txt |
| GPU test pod wide | evidence/gpu-runtime-test-pod-wide.txt |
| nvidia-smi output | logs/gpu-runtime-test-nvidia-smi.log |
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

### nvidia-smi output (summary)

```
Sun Jul 19 16:49:33 2026
+-----------------------------------------------------------------------------+
| NVIDIA-SMI 535.183.01   Driver Version: 535.183.01   CUDA Version: 12.2    |
|-------------------------------+----------------------+----------------------+
| GPU  Name        Persistence-M| Bus-Id        Disp.A | Volatile Uncorr. ECC |
| Fan  Temp  Perf  Pwr:Usage/Cap|         Memory-Usage | GPU-Util  Compute M. |
|===============================+======================+======================|
|   0  Quadro RTX 6000     Off  | 00000000:17:00.0 Off |                  Off |
| N/A   56C    P0    60W / 260W |      0MiB / 22502MiB |      0%      Default |
+-------------------------------+----------------------+----------------------+
```

## 5. Conclusion

Status: PASSED

NVIDIA runtime fully operational. Container with `nvidia.com/gpu: 1` successfully executed `nvidia-smi` on n8 (control-plane). GPU Quadro RTX 6000 (driver 535.183.01, CUDA 12.2) visible and functional.

## 6. Failed / Partial items

| Item | Status | Reason | Required fix |
|---|---|---|---|
| — | PASSED | — | — |
