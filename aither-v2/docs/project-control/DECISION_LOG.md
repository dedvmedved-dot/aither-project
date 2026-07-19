# Decision Log

| ID | Date | Decision | Rationale | Status |
|---|---|---|---|---|
| DEC-TP-01 | 2026-07 | TP=1 accepted for MVP | Stage 02 60-minute load test passed without HTTP errors, timeouts, restarts, or GPU OOM | ACCEPTED |
| DEC-TP-02 | 2026-07 | TP=2 postponed to Post-MVP Optimization | TP=2 adds NCCL and multi-GPU scheduling risk and is not needed for current MVP | POSTPONED |
| DEC-OAUTH-01 | 2026-07 | OAuth removed from immediate MVP | Reduces MVP complexity; can be revisited later | ACCEPTED |
| DEC-GW-01 | 2026-07 | Gateway must be hardened before BFF/Portal | Gateway is part of user-facing inference control plane | ACCEPTED |
| DEC-AUDIT-01 | 2026-07 | Stage transition requires ChatGPT external audit | Prevents premature status escalation by Hermes | ACCEPTED |
| DEC-ACCESS-01 | 2026-07-20 | GitHub connector/API is accepted as primary ChatGPT repository audit path | Raw/blob web access may be affected by CDN/cache/tool limitations | ACCEPTED |
| DEC-AUDIT-02 | 2026-07-20 | Stage 05 remains blocked until explicit ChatGPT task is issued | Prevents Hermes self-transition | ACCEPTED |
| DEC-LOG-01 | 2026-07-20 | Chat sessions are committed as structured session logs, not raw full transcripts | Keeps repository readable and auditable | ACCEPTED |
