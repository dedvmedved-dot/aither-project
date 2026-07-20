# Findings Register

| ID | Finding | Status | Target |
|---|---|---|---|
| GW-01 | nginx-gateway-32b previously had 1 Running Pod and 2 ImagePullBackOff Pods | RESOLVED | Stage 04 |
| TP3-NCCL-01 | Stage 03 report claimed NCCL usage observed without explicit evidence | RESOLVED | Stage 04 docs correction |
| 32B-DIRECT-CHAT-01 | Direct vLLM 32B chat can bypass gateway restriction | ACCEPTED FOR MVP INTERNAL SCOPE | Stage 05/07/08 |
| GW-RL-01 | Gateway/BFF rate limiting not finalized | POSTPONED | Stage 06 |
| GW-IMG-01 | Image digest pinning not completed; version tag is used because digest pull failed over VPN | RISK ACCEPTED / PARTIAL | Post-MVP or Stage 08 |
| GW-SC-01 | Gateway securityContext is partial; runAsNonRoot/readOnlyRootFilesystem not enabled due nginx compatibility | PARTIAL | Stage 08 |
| ACCESS-01 | ChatGPT raw/blob access issue | RESOLVED | GitHub connector/API used as audit path |
| PROD-READY-01 | MVP is not production-ready yet | OPEN | Stage 11 RC1 |
| **BFF-01** | **BFF deployed and running (FastAPI, 1/1 Running, 0 restarts)** | **PASSED** | **Stage 05** |
| **BFF-IMPL-01** | **BFF implementation mismatch resolved: app.py source matches deployed workload** | **RESOLVED** | **Stage 05** |
| **BFF-ROUTE-01** | **32B completion routes through nginx-gateway-32b (never direct vLLM)** | **PASSED** | **Stage 05** |
| **BFF-CHAT-32B-01** | **32B chat blocked by BFF before upstream (HTTP 422 confirmed)** | **PASSED** | **Stage 05** |
| **BFF-DIRECT-01** | **Direct vLLM 32B user-facing bypass not present** | **PASSED** | **Stage 05** |
| **BFF-RL-01** | **Rate limiting postponed to Stage 06** | **SUPERSEDED (see BFF-RL-01 PASSED)** | **Stage 06** |
| **BFF-AUTH-01** | **BFF has no built-in auth; relies on upstream auth** | **PARTIAL** | **Stage 08** |
| **BFF-SEC-01** | **BFF container securityContext applied (runAsNonRoot, cap drop, read-only app volume)** | **PASSED** | **Stage 05** |
| **BFF-STATUS-01** | **BFF correctly propagates upstream HTTP status codes** | **PASSED** | **Stage 05** |
| **BFF-TOKEN-01** | **Valid token test for 32B completion not collected (VPN instability)** | **NOT COLLECTED** | **Stage 05** |
| **BFF-RL-01** | **Rate limiting implemented in Stage 06** | **PASSED** | **Stage 06** |
| **BFF-RL-REDIS-01** | **Redis-backed fixed-window rate limiting deployed** | **PASSED** | **Stage 06** |
| **BFF-RL-429-01** | **HTTP 429 returned when limit exceeded** | **PASSED** | **Stage 06** |
| **BFF-RL-KEY-01** | **Rate limit key does not store raw Authorization token** | **PASSED** | **Stage 06** |
| **BFF-RL-RESET-01** | **Rate limit window reset verified** | **PASSED** | **Stage 06** |
| **BFF-RL-REDIS-FAIL-01** | **Redis unavailable behaviour (fail-open)** | **PARTIAL** | **Stage 06** |
| **BFF-RL-RESET-TTL-01** | **TTL reset not directly observed; reset verified by manual Redis key flush** | **MINOR FINDING** | **Stage 06/Post-MVP** |
| **AUTH-01** | **BFF central auth implemented** | **CORRECTIVE IN PROGRESS** | **Stage 07.1** |
| **AUTH-API-TOKEN-01** | **API token issuance implemented** | **CORRECTIVE IN PROGRESS** | **Stage 07.1** |
| **AUTH-RL-429-01** | **Rate limiting still returns 429 on BFF v0.4.0 after auth integration** | **PASSED (burst 15 reqs: 10×200 + 5×429)** | **Stage 07.1** |
| **AUTH-UPSTREAM-VALID-01** | **Internal upstream tokens are test-only; end-to-end model 200 not confirmed** | **PARTIAL** | **Stage 07.1** |
| **AUTH-TOKEN-HASH-01** | **Raw API tokens are not stored** | **PASSED (code review + runtime)** | **Stage 07.1** |
| **AUTH-TOKEN-REVOKE-01** | **API token revoke works** | **PASSED (runtime confirmed)** | **Stage 07.1** |
| **AUTH-AGENT-01** | **AI agent can call models through API token** | **PASSED (runtime confirmed — BFF auth flow works)** | **Stage 07.1** |
| **AUTH-UPSTREAM-01** | **User API token is not forwarded to upstream vLLM/gateway** | **PASSED (code review + runtime confirmed)** | **Stage 07.1** |
| **AUTH-REDIS-FAIL-01** | **Auth/token store unavailable behavior (Redis)** | **PARTIAL** | **Stage 07.1** |
| **AUTH-TOKEN-PERSIST-01** | **Token metadata durability with Redis-only storage** | **PARTIAL** | **Stage 07.1/Post-MVP** |
| **AUTH-PORTAL-01** | **Portal auth UI not implemented in Stage 07.1** | **TARGET Stage 07.2** | **Stage 07.2** |
| **AUTH-OAUTH-01** | **OAuth not implemented** | **OUT OF SCOPE / FUTURE** | **Future** |
| **MODEL-32B-CHAT-ADAPTER-01** | **32B chat adapter over completion endpoint** | **PASSED (runtime confirmed — adapter logic works)** | **Stage 07.1** |
