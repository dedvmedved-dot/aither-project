# Aither Product Roadmap

**Document:** `docs/roadmap.md`  
**Version:** 1.0  
**Date:** 2026-07-23

---

## Overview

This roadmap defines the planned evolution of the Aither AI Platform from Beta v0.9 through Version 1.1 and beyond. It serves as the guiding document for all future development and release planning.

---

## Beta v0.9 — Pilot Release (Current)

**Status:** READY FOR PILOT USERS (pending external audit)

### Scope

- **Single model:** qwen-32b-base (completion, via vLLM 32B through Gateway)
- **Portal UI:** Login, Dashboard, Chat with assistant, Model display, API Key management
- **Auth:** JWT-based authentication (admin/admin), API Key-based authentication for OpenAI-compatible endpoint
- **Conversations:** Full CRUD via Portal Backend → AI Platform → Gateway → vLLM
- **Chat persistence:** SQLite storage, survives refresh and re-login
- **API Key management:** Create, list, revoke with SHA256 hashing
- **OpenAI-compatible:** `/v1/chat/completions` with API Key auth
- **Infrastructure:** Kubernetes cluster (2 nodes: n7 + n8), in-cluster Docker registry, nginx Gateway

### Known Limitations

- One model only (qwen-32b-base, completion-only)
- No external DNS / public ingress
- K8s API intermittency from build host
- No automated backups
- Basic health checking (no `/live` endpoint, no dependency-aware readiness)
- Rate limiting configured but not enforced at Gateway level

---

## RC1 — Production Readiness (Current Stage)

**Status:** IN PROGRESS

### Scope

- Production configuration audit
- Security hardening (CORS, secrets, rate limiting)
- Backup & recovery procedures
- Comprehensive healthcheck endpoints (`/health`, `/ready`, `/live`)
- Structured logging
- Load testing (5/10/20 concurrent users)
- Failover testing (pod restart recovery)
- Operational documentation

---

## Version 1.0 — Stable Release

**Target:** After RC1 acceptance + Pilot feedback

### Scope

- All RC1 items hardened
- Public ingress with HTTPS (TLS termination)
- External DNS (portal.aither.example.com)
- Rate limiting at Gateway level with Redis
- Enhanced monitoring with Prometheus + Grafana dashboards
- Alerting (PagerDuty / Slack webhook)
- Automated CI/CD pipeline
- User management (self-registration, password reset)
- Session timeout and token refresh
- Audit logging (all admin actions logged)

### Estimated Effort

| Area | Effort | Priority |
|------|--------|----------|
| Public ingress + TLS | Medium | Critical |
| Monitoring + Alerting | Medium | High |
| CI/CD | Medium | High |
| User self-service | Low | Medium |
| Session management | Low | Medium |

---

## Version 1.1 — Multi-Model Support

**Target:** After Version 1.0

### Scope

#### Multi-Model Support

The following items are planned for Version 1.1:

- **Restore qwen-14b-instruct** — Re-enable the 14B chat model that was disabled in RC1. Requires proper integration through the Gateway or a dedicated routing layer.
- **Universal LLM Gateway** — Replace the current single-upstream nginx Gateway (`nginx-gateway-32b`) with a multi-upstream Gateway capable of routing to multiple vLLM backends.
- **Model-aware routing** — The Gateway must route requests based on the model name in the request (e.g., `/v1/chat/completions` with `model=qwen-32b-base` → vLLM 32B, `model=qwen-14b-instruct` → vLLM 14B).
- **Multiple vLLM backends** — Support for two or more vLLM instances running different model sizes/architectures simultaneously.
- **Chat + Completion support** — Ensure proper format handling: chat models (`qwen-14b-instruct`) via `/v1/chat/completions`, completion models (`qwen-32b-base`) via `/v1/completions`.
- **Dynamic model selection** — Allow administrators to add/remove models without Gateway reconfiguration (model registry integration).
- **Scaling** — Support horizontal scaling of vLLM backends (multiple replicas per model).
- **Load balancing** — Distribute requests across replicas of the same model based on load.

#### Other V1.1 Items

- Multi-user support with role-based access control (RBAC)
- Conversation search and filtering
- Streaming responses (SSE) from Portal UI
- File uploads and context injection
- Prompt templates library
- Usage quotas per user/API Key

### Multi-Model Architecture Design Principles

1. **Backward compatibility** — All existing v0.9/1.0 endpoints must continue to work unchanged.
2. **Gateway-driven routing** — The Gateway (not AI Platform) determines which backend to route to based on model name.
3. **Registry-backed** — Model-to-backend mapping is driven by the Model Registry (AI Platform DB), not hardcoded.
4. **Graceful degradation** — If a backend is unavailable, the Gateway returns a clear error rather than failing silently.

### Estimated Effort

| Area | Effort | Priority |
|------|--------|----------|
| Universal LLM Gateway | High | Critical |
| Model-aware routing | Medium | Critical |
| Multi-backend support | High | High |
| Chat + Completion routing | Medium | High |
| Dynamic model selection | Medium | Medium |
| Scaling + Load balancing | High | Medium |

---

## Future (Post v1.1)

- **Fine-tuning API** — Allow users to fine-tune models on their data
- **Function calling / Tools** — OpenAI-compatible function calling
- **Batch processing** — Async batch inference for large workloads
- **Model marketplace** — Share/deploy community models
- **Enterprise SSO** — SAML/OIDC integration
- **Audit trail** — Immutable audit log for compliance

---

## Release Cadence

| Version | Target Timeline | Type |
|---------|----------------|------|
| Beta v0.9 | July 2026 | Pilot |
| RC1 | July 2026 | Production readiness |
| V1.0 | August 2026 | Stable |
| V1.1 | September 2026 | Feature |
| Future | Q4 2026+ | Growth |
