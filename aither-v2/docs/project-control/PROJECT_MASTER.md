# Aither / AI Hermes MVP — Project Master

## 1. Project Identity

Project name: Aither / AI Hermes MVP  
Repository: https://github.com/dedvmedved-dot/aither-project  
Branch: aither-v2  
Working directory: aither-v2/

## 2. Roles

| Role | Responsibility |
|---|---|
| Owner | Final approval and project direction |
| Hermes + DeepSeek | Implementation, evidence collection, commits |
| ChatGPT | Architect, task author, external auditor |
| GitHub | Persistent source of truth |

## 3. Operating Model

1. ChatGPT writes a stage task.
2. Owner gives task to Hermes.
3. Hermes executes and commits.
4. Owner sends commit hash and links to ChatGPT.
5. ChatGPT audits raw GitHub evidence.
6. ChatGPT returns PASSED / PARTIAL / FAILED / CORRECTIVE REQUIRED.
7. Next stage starts only after external audit.

## 4. Current MVP Status

| Stage | Name | Status |
|---|---|---|
| Stage 01 | Cluster/GPU Baseline | PASSED WITH FINDINGS |
| Stage 02 | Inference Acceptance | PASSED WITH FINDINGS |
| Stage 03 | TP=2 Decision | PASSED WITH MINOR CORRECTION REQUIRED |
| Stage 04 | Gateway Hardening | PASSED WITH FINDINGS / CONNECTOR VERIFIED |
| Stage 04.1 | Repository Integrity Verification | PASSED / CONNECTOR VERIFIED |
| Stage 05 | BFF Acceptance | **PASSED WITH FINDINGS / CONNECTOR VERIFIED** |
| Stage 06 | Redis / Rate Limiting | **PASSED WITH FINDINGS / CONNECTOR VERIFIED** |
| Stage 07.1 | Auth / API Token / Agent Access Baseline | **PASSED WITH FINDINGS / CONNECTOR VERIFIED** |
| Stage 07.2 | Portal UI with Auth, Token Management and Chat Access | **PASSED WITH FINDINGS / CONNECTOR VERIFIED** |
| Stage 08 | MVP End-to-End Runtime Acceptance | **PASSED WITH FINDINGS / CONNECTOR VERIFIED** |
| Stage 09 | NOT APPROVED | NOT APPROVED |


## 5. Accepted Decisions

| ID | Decision | Status |
|---|---|---|
| DEC-TP-01 | TP=1 accepted for MVP | ACCEPTED |
| DEC-TP-02 | TP=2 postponed to Post-MVP Optimization | POSTPONED |
| DEC-OAUTH-01 | OAuth removed from immediate MVP scope | ACCEPTED |
| DEC-GW-01 | Gateway must be hardened before BFF/Portal stages | ACCEPTED |
| DEC-AUDIT-01 | Hermes cannot approve transition to next stage without ChatGPT audit | ACCEPTED |

## 6. Current Known Risks

| Risk | Status |
|---|---|
| Gateway previously had ImagePullBackOff pods | RESOLVED |
| Direct 32B vLLM access may bypass gateway policy | Accepted for MVP internal scope, controlled by BFF routing |
| TP=2 not tested | Accepted; postponed |
| Rate limiting finalized | Target Stage 06 (PASSED WITH FINDINGS) |
| BFF valid token test not collected | VPN instability blocked kubectl secret retrieval |
| Production readiness not achieved | Not production-ready |

## 7. MVP Principle

The MVP is accepted only when all required stages have evidence, logs, reports, and external audit approval.

No stage can be declared complete based only on intent or generated documentation.
Evidence must precede conclusion.
