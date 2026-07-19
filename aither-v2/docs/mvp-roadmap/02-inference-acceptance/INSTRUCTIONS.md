# Stage 02 — Inference Acceptance

## Goal

Доказательно подтвердить работоспособность inference-слоя MVP:
- 14B model endpoint;
- 32B model endpoint;
- gateway path;
- endpoint restrictions;
- smoke benchmark;
- 60-minute endurance/load test;
- streaming TTFT.

## Scope

Разрешено:
- read-only kubectl;
- benchmark Jobs;
- curl/http проверки;
- сбор logs/evidence;
- benchmark scripts.

Запрещено:
- менять production vLLM manifests;
- менять gateway manifests;
- чинить gateway ImagePullBackOff в этом этапе;
- менять BFF/Portal/Redis/OAuth.

## Required outputs

- vllm-service-inventory.md
- 32b-benchmark-report.md
- LOAD_TEST_60MIN_REPORT.md
- streaming-ttft-report.md
- evidence/*
- logs/*
