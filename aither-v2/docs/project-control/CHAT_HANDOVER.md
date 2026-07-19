# Chat Handover Context

Use this text to start a new ChatGPT project or chat.

```text
Project: Aither / AI Hermes MVP.

GitHub:
https://github.com/dedvmedved-dot/aither-project

Branch:
aither-v2

Working directory:
aither-v2/

Role of ChatGPT:
- technical architect;
- task author for Hermes + DeepSeek;
- external auditor;
- stage acceptance authority.

Role of Hermes:
- implementation;
- evidence collection;
- logs/reports creation;
- GitHub commits.

Current status:
Stage 01 — Cluster/GPU Baseline: PASSED WITH FINDINGS.
Stage 02 — Inference Acceptance: PASSED WITH FINDINGS.
Stage 03 — TP=2 Decision: PASSED WITH MINOR CORRECTION REQUIRED.
|Stage 04 — Gateway Hardening: PASSED WITH FINDINGS / CONNECTOR VERIFIED.
|Stage 04.1 — Repository Integrity Verification: PASSED / CONNECTOR VERIFIED.
|Stage 05 — BFF Acceptance: NOT STARTED / NOT APPROVED.

Key decisions:
TP=1 accepted for MVP.
TP=2 postponed to Post-MVP Optimization.
OAuth removed from immediate MVP.
Gateway accepted with findings (GW-IMG-01, GW-SC-01, GW-RL-01).
Direct vLLM 32B access is not user-facing for MVP.
Hermes must not change vLLM/GPU/TP/BFF/Portal/Redis/OAuth outside approved scope.

Repository access:
ChatGPT repository access was restored via GitHub connector/API.
Use GitHub connector/API for future audits instead of relying only on raw/blob web fetch.

Audit rule:
No transition to the next stage without external ChatGPT audit.

Hermes behavior rules:
- evidence first, conclusion second;
- do not overstate status;
- do not hide failures;
- preserve logs and evidence;
- use raw GitHub links;
- report all PARTIAL/FAILED findings.
```
