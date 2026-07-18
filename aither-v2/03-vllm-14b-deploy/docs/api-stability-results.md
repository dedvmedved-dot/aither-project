# API Stability Test Results

**Date:** 2026-07-19

## 1. kubectl get nodes --request-timeout=5s (30 запросов)

| Metric       | Count |
|-------------|-------|
| **Success** | 29    |
| **Timeout** | 1     |
| **Total**   | 30    |

**Success rate:** 96.7%

**Notes:**
- 1 timeout occurred on the very first request (RESULT_1). All subsequent 29 requests succeeded.
- The single timeout may be related to a cold-start connection to the API server on the first call.

## 2. kubectl top node

| Node                          | CPU(cores) | CPU(%) | MEMORY(bytes) | MEMORY(%) |
|------------------------------|-----------|--------|---------------|-----------|
| bootsmam-k8s-clnt01-n7-gpu   | 101m      | 0%     | 7385Mi        | 0%        |
| bootsman-k8s-clnt01-n8-gpu   | 503m      | 0%     | 72880Mi       | 9%        |

## 3. kubectl top pod -A (top 10 by CPU)

| Namespace      | Pod                                                          | CPU(cores) | MEMORY(bytes) |
|---------------|-------------------------------------------------------------|-----------|---------------|
| aiops          | clickhouse-b8bc47f4c-mdt48                                  | 78m       | 2013Mi        |
| kube-system    | kube-apiserver-bootsman-k8s-clnt01-n8-gpu                   | 42m       | 684Mi         |
| kube-system    | etcd-bootsman-k8s-clnt01-n8-gpu                             | 30m       | 76Mi          |
| kube-flannel   | kube-flannel-ds-wjkxf                                       | 17m       | 20Mi          |
| kube-system    | kube-controller-manager-bootsman-k8s-clnt01-n8-gpu          | 16m       | 77Mi          |
| kube-system    | kube-scheduler-bootsman-k8s-clnt01-n8-gpu                   | 13m       | 37Mi          |
| kube-flannel   | kube-flannel-ds-t2q2q                                       | 13m       | 21Mi          |
| gpu-operator   | gpu-feature-discovery-sr2qp                                 | 13m       | 43Mi          |
| gpu-operator   | nvidia-dcgm-exporter-lvx6h                                  | 10m       | 456Mi         |

## Summary

- **API stability is good:** 29/30 (96.7%) requests succeeded within 5s timeout. The single timeout was on the first request only.
- **Cluster topology:** 2 nodes — 1 control-plane (n8-gpu) + 1 worker (n7-gpu).
- **Top resource consumers:** ClickHouse (aiops namespace) uses the most CPU and memory among pods.
