# Stage 03 — TP=2 Decision

## Goal

Доказательно зафиксировать текущий Tensor Parallelism режим и принять решение:
- TP=1 accepted for MVP;
- TP=2 postponed to Post-MVP Optimization.

## Scope

Разрешено:
- read-only kubectl;
- чтение deployment/pod specs;
- чтение logs;
- оформление decision report.

Запрещено:
- менять vLLM Deployments;
- менять GPU limits;
- включать TP=2;
- менять gateway/BFF/Portal/Redis;
- переходить к Stage 04 без аудита.

## Required outputs

- tp2-decision-report.md
- evidence/*
- logs/*
- updated current-mvp-status.md
