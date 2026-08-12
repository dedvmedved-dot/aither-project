# TASK: CODEX-HARNESS-S2-AUTONOMOUS-CANARY

## MODE
AUTONOMOUS CANARY

This is the first task intended to be transported from GitHub to Codex entirely by the host supervisor, with no Owner copy/paste.

## Authorized implementation
Create exactly one file:

`.agent/CANARY_RESULT.md`

with exactly this content:

```text
# Autonomous Codex Canary

TASK: CODEX-HARNESS-S2-AUTONOMOUS-CANARY
RESULT: PASS
TRANSPORT: GITHUB -> HOST SUPERVISOR -> CODEX
OWNER_COPY_PASTE_REQUIRED: NO
```

A trailing newline is required.

Do not modify any other file.

## Executor restrictions
- no Git metadata writes;
- no git fetch/pull/commit/push;
- no Kubernetes;
- no deployment;
- no DB/runtime mutation;
- no secrets;
- no package installation;
- no application code changes;
- no autonomous next task.

The host supervisor, not Codex, owns validation, staging, commit and push after the executor returns.

Return PASS/FAIL/BLOCKED and STOP. Do not declare PASSED or CONNECTOR VERIFIED.
