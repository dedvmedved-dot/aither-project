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
