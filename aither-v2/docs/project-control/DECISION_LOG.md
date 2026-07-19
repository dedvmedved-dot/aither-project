# Decision Log

| ID | Date | Decision | Rationale | Status |
|---|---|---|---|---|
| DEC-TP-01 | 2026-07 | TP=1 accepted for MVP | Stage 02 60-minute load test passed without HTTP errors, timeouts, restarts, or GPU OOM | ACCEPTED |
| DEC-TP-02 | 2026-07 | TP=2 postponed to Post-MVP Optimization | TP=2 adds NCCL and multi-GPU scheduling risk and is not needed for current MVP | POSTPONED |
| DEC-OAUTH-01 | 2026-07 | OAuth removed from immediate MVP | Reduces MVP complexity; can be revisited later | ACCEPTED |
| DEC-GW-01 | 2026-07 | Gateway must be hardened before BFF/Portal | Gateway is part of user-facing inference control plane | ACCEPTED |
| DEC-AUDIT-01 | 2026-07 | Stage transition requires ChatGPT external audit | Prevents premature status escalation by Hermes | ACCEPTED |
