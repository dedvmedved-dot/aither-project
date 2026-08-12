# CODEX-HARNESS-S2-HOST-BOOTSTRAP-R2

Architect-owned correction; do not execute with Codex.

Corrections:
- `--ask-for-approval never` remains a global Codex option before `exec`;
- `--sandbox workspace-write` is now passed to the `exec` subcommand after `exec`;
- installer publishes a safe Git tag containing only success/failure stage and UTC timestamp, so Architect can diagnose bootstrap without Owner log copy/paste.

The next Architect commit publishes autonomous canary V3.
