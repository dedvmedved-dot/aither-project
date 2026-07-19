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
| **BFF-RL-01** | **Rate limiting postponed to Stage 06** | **POSTPONED** | **Stage 06** |
| **BFF-AUTH-01** | **BFF has no built-in auth; relies on upstream auth** | **PARTIAL** | **Stage 08** |
| **BFF-SEC-01** | **BFF container securityContext applied (runAsNonRoot, cap drop, read-only app volume)** | **PASSED** | **Stage 05** |
| **BFF-STATUS-01** | **BFF correctly propagates upstream HTTP status codes** | **PASSED** | **Stage 05** |
| **BFF-TOKEN-01** | **Valid token test for 32B completion not collected (VPN instability)** | **NOT COLLECTED** | **Stage 05** |
