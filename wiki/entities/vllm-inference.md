---
title: vLLM Inference
created: 2026-07-09
updated: 2026-07-09
type: entity
tags: [vllm, inference, models, architecture]
sources: []
---

# vLLM Inference

Сервис инференса LLM на базе vLLM. Развёрнут в Kubernetes на узлах
с GPU NVIDIA RTX 6000.

## Конфигурация

| Параметр | n7 (worker) | n8 (control-plane) |
|---|---|---|
| GPU | 2× RTX 6000 (24 GB) | 2× RTX 6000 (24 GB) |
| Модели | Qwen2.5-32B-Instruct, Qwen2.5-Coder-14B | — |
| Tensor Parallelism | TP=2 | — |
| Порт | 8000 | — |

## Модели

- **Qwen2.5-32B-Instruct** (32B параметров, TP=2) — основная модель для reasoning
- **Qwen2.5-Coder-14B** (14B параметров) — специализированная для кода

## Интеграция

vLLM получает запросы через [[AI Gateway]], который выполняет:
- Rate limiting ([[Redis]])
- Резервирование токенов ([[Billing System]])
- Content filtering ([[Security Ingress]] / [[Security Egress]])

Модели загружаются из `/mnt/models/` на n7 через hostPath.
Для production-масштабирования требуется [[NVLink]] и модели 70B+.

## Performance

- Qwen2.5-32B: ~15-20 токенов/с на TP=2
- Qwen2.5-Coder-14B: ~25-30 токенов/с
- TTFT: ~200-500ms (зависит от длины контекста)

Мониторинг через [[Prometheus]] + [[DCGM]] → [[Grafana]].
