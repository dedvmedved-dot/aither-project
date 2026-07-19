# BFF Inventory Report

Date: 2026-07-20
Executor: hermes@vps2
Repository branch: aither-v2
Commit: (this commit)

## 1. Repository inventory

- No existing BFF implementation found in repository.
- Stage 05 created:
  - `tools/bff/app.py` — Python FastAPI BFF
  - `tools/bff/Dockerfile` — Docker build
  - `tools/bff/requirements.txt` — Python deps
  - `tools/bff/README.md` — Documentation

## 2. Kubernetes inventory

- No existing BFF in aither-inference namespace.
- Stage 05 created:
  - `configmap/aither-bff-config` — nginx BFF config
  - `deployment/aither-bff` — 1 replica, nginx:alpine
  - `service/aither-bff` — ClusterIP :8000

## 3. Existing BFF found

**No.** Minimal MVP BFF was created.

## 4. BFF routing

- `/health` → 200 (nginx)
- `/api/v1/chat` → proxies to vllm-14b-instruct for 14B, or to gateway (which blocks 32B chat with 422)
- `/api/v1/completions` → proxies to nginx-gateway-32b (which enforces auth + chat block)
- `/api/v1/models` → 200 (static list)
- Unknown paths → 404

## 5. Risks

- BFF chat goes through gateway, not direct vLLM for 32B (correct for policy).
- 14B chat goes to vllm-14b-instruct directly (approved 14B path).
- Gateway auth required for 32B completion (VLLM_API_KEY must be passed by client).
- No rate limiting (postponed to Stage 06).
