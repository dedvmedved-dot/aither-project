# Stage 04 — Gateway Hardening

## Goal

Закрыть GW-01 и доказательно подтвердить MVP-hardening gateway:
- pod/rollout status;
- auth;
- endpoint policy;
- image pinning;
- resources;
- securityContext;
- logs;
- direct 32B access policy.

## Scope

Разрешено:
- read-only kubectl;
- hardened gateway manifest in manifests/mvp-roadmap/04-gateway/;
- gateway auth/endpoint tests;
- documentation updates;
- Stage 03 NCCL wording correction.

Запрещено:
- менять vLLM Deployments;
- менять GPU limits;
- включать TP=2;
- менять BFF/Portal/Redis/OAuth;
- переходить к Stage 05 без аудита.

## Required outputs

- gateway-auth-report.md
- gateway-hardening-report.md
- evidence/*
- logs/*
- nginx-gateway-32b-hardened.yaml
