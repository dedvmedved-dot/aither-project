# Stage 01 — Cluster/GPU Baseline

## Goal

Доказательно зафиксировать фактическую топологию Kubernetes-кластера, роли n7/n8, размещение vLLM/gateway/benchmark и работоспособность NVIDIA runtime.

## Scope

Разрешено:
- выполнять read-only kubectl-команды;
- создать временный Pod `gpu-runtime-test`;
- сохранить evidence-файлы;
- удалить временный Pod после проверки.

Запрещено:
- менять vLLM Deployments;
- менять gateway;
- менять Portal/BFF/Redis;
- менять GPU Operator;
- менять containerd/runtime configuration.

## Required outputs

- cluster-topology-report.md
- gpu-runtime-validation.md
- evidence/*.txt
- logs/*.log
- manifests/mvp-roadmap/01-cluster-gpu/gpu-runtime-test.yaml
