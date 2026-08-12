# TASK: CODEX-HARNESS-S2-AUTONOMOUS-CANARY-V3

## MODE
AUTONOMOUS CANARY

This task must be transported from GitHub to Codex entirely by the host supervisor. The Owner must not copy/paste this task into Codex.

Create exactly `.agent/CANARY_RESULT.md` with exactly:

```text
# Autonomous Codex Canary

TASK: CODEX-HARNESS-S2-AUTONOMOUS-CANARY-V3
RESULT: PASS
TRANSPORT: GITHUB -> HOST SUPERVISOR -> CODEX
OWNER_COPY_PASTE_REQUIRED: NO
```

A trailing newline is required. Do not modify any other file. Do not write Git metadata, fetch/pull/commit/push, access Kubernetes, deployment, DB/runtime, secrets, packages, or application code.

The host supervisor owns validation, staging, commit and push. Return PASS/FAIL/BLOCKED and STOP. Do not declare PASSED or CONNECTOR VERIFIED.
