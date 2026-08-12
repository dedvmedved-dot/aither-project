# TASK: CODEX-HARNESS-S2-AUTONOMOUS-CANARY-V2

## MODE
AUTONOMOUS CANARY

This task must be transported from GitHub to Codex entirely by the host supervisor. The Owner must not copy/paste this task into Codex.

## Authorized implementation
Create exactly one file:

`.agent/CANARY_RESULT.md`

with exactly this content, including the final newline:

```text
# Autonomous Codex Canary

TASK: CODEX-HARNESS-S2-AUTONOMOUS-CANARY-V2
RESULT: PASS
TRANSPORT: GITHUB -> HOST SUPERVISOR -> CODEX
OWNER_COPY_PASTE_REQUIRED: NO
```

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

The host supervisor owns validation, staging, commit and push. Validation fails closed if the expected canary file is absent or its content differs.

Return PASS/FAIL/BLOCKED and STOP. Do not declare PASSED or CONNECTOR VERIFIED.
