# TASK: HERMES-INTEGRATION-H7B-AUTONOMOUS-RESULT-ONLY-CANARY

## Goal

Prove the complete autonomous reverse feedback path after H7A/H7A-R1:

`Architect GitHub task -> persistent scheduler -> Hermes -> host validation -> runner-managed EXECUTION_RESULT.json -> one result-only Git commit/push -> next poll IDLE`.

This is a strict read-only executor canary. No implementation/source changes are authorized.

## Starting state

- Branch: `aither-v2`.
- Baseline: `a9b8b4641e8eddfac950f076aaa68dbbd0779891`.
- H6 persistent scheduler accepted.
- H7A result-publication layer installed.
- H7A-R1 fixed ownership verification to fail closed using non-following metadata.
- `.agent/EXECUTION_RESULT.json` already exists from H7A-R1 and is runner-managed.

## Executor semantics

Root Hermes must only:

1. read `AGENTS.md`, `.agent/CURRENT_TASK.json`, `.agent/CURRENT_TASK.md`;
2. verify task id is `HERMES-INTEGRATION-H7B-AUTONOMOUS-RESULT-ONLY-CANARY`;
3. verify `executor=hermes`, `source_write=false`, `agent_exec=true`;
4. inspect branch/HEAD/worktree read-only;
5. make no repository/source/runtime/Kubernetes/database/deployment/package/secret changes;
6. return PASS and STOP.

No direct/manual service, runner, observer, H2 or Hermes launch is authorized. The persistent scheduler must discover this task itself.

## Expected host-runner behavior

After Hermes returns successfully:

- changed implementation paths must be empty;
- existing validations must pass;
- host runner alone overwrites `.agent/EXECUTION_RESULT.json` with the H7B safe whitelist payload;
- exactly one result-only commit is created and pushed with message `test: publish autonomous H7B result`;
- commit must contain only `.agent/EXECUTION_RESULT.json`;
- result payload must contain `task_id`, `task_fingerprint`, `executor=hermes`, `result=PASS`, `start_head`, empty `changed_paths`, empty `implementation_paths`, safe message field;
- no stdout/stderr/env/prompt/secret data is allowed;
- runner state records successful H7B fingerprint and result commit SHA;
- next unchanged scheduler poll must return IDLE without invoking observer/H2/root Hermes/Codex again;
- no second result commit may be created.

## Hard prohibitions

DO NOT:

- modify source files;
- modify CURRENT_TASK locally;
- modify EXECUTION_RESULT directly from Hermes;
- manually start timer/service/runner/observer/H2/Hermes;
- invoke Codex;
- stop/disable scheduler on PASS;
- restart/reconfigure Telegram Gateway;
- touch Aither runtime/Kubernetes/database/deployment;
- expose secrets;
- modify sudoers, ownership or safe.directory.

## PASS criteria

PASS only if:

1. task is autonomously discovered by persistent scheduler;
2. root Hermes executes exactly once for H7B fingerprint;
3. executor changes zero files;
4. validations pass;
5. host runner publishes `.agent/EXECUTION_RESULT.json` automatically;
6. exactly one result-only commit is pushed;
7. result payload is safe and identifies H7B/PASS/hermes with empty implementation paths;
8. next same-fingerprint poll is IDLE with no executor reinvocation;
9. no extra commit appears for same fingerprint;
10. scheduler remains enabled+active;
11. Telegram Gateway remains unchanged;
12. no Aither/Kubernetes/database/runtime mutation;
13. no secret values printed.

Do not declare Architect acceptance. STOP.
