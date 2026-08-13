# TASK: HERMES-INTEGRATION-H1-EXECUTOR-ABSTRACTION

## Goal
Extend the existing Aither host supervisor so a task can select `executor=codex` or `executor=hermes`, while preserving all existing fail-closed Git/scope/capability behavior.

This task modifies only `.agent` management harness files. It MUST NOT touch Aither application/runtime code, Kubernetes, databases, deployment, Hermes configuration, Telegram configuration, systemd installation, secrets, or packages.

## Confirmed runtime facts from Owner/Hermes
Treat these as task input; do not reconfigure them:
- Hermes and Codex are on the same VPS.
- Existing Telegram-connected Hermes: version v0.20.0.
- Telegram is served by existing Hermes Gateway.
- Hermes CLI supports one-shot non-interactive mode: `hermes -z "prompt"`.
- No Hermes local API server is currently required for integration.
- Telegram must continue working and MUST NOT be restarted or reconfigured.

## Required implementation

### 1. Task executor field
Update task validation in `.agent/host_task_runner.py` so `executor` is required and must be exactly `codex` or `hermes`.

The current task contains `executor=codex`, so migration is fail-closed and immediately self-hosting.

### 2. Executor dispatch
Preserve the existing Codex argv behavior exactly for `executor=codex`.

Add Hermes dispatch for `executor=hermes` using a dedicated builder such as `build_hermes_argv()` and a generic `build_executor_argv(task)` dispatcher.

Hermes invocation contract:
- invoke a local executable only;
- no shell interpolation;
- use argv list;
- one-shot mode `-z`;
- fixed governed prompt instructing Hermes to read `AGENTS.md`, `.agent/CURRENT_TASK.json`, `.agent/CURRENT_TASK.md`, execute only the current task, obey capabilities/scope, return final report and STOP;
- executable must be overridable by environment, e.g. `HERMES_BIN` or `AITHER_REAL_HERMES_BIN`;
- safe default may resolve `hermes` from PATH.

Do NOT embed secrets, Telegram credentials, root credentials, API tokens, or environment dumps.

### 3. Hermes observer
Create `.agent/hermes_observer.py` as a small wrapper for Hermes one-shot execution.

Requirements:
- execute the real Hermes binary as an argv list, never `shell=True`;
- do not parse or publish Hermes reasoning/output into live status;
- emit sanitized heartbeat/live state through existing `runner_live.py` while Hermes is alive;
- live state must include `executor=hermes`, task id, process_alive, heartbeat, phase, and safe result/exit metadata only;
- stdout/stderr may pass back to the parent process but MUST NOT be copied into `runner-live`;
- hard timeout configurable by environment with a safe default matching current runner expectations;
- terminate/kill child on timeout and return non-zero;
- no Telegram interaction, no second gateway, no service restart.

### 4. Live schema
Extend `.agent/runner_live.py` safe schema with at least:
- `executor`
- `repo_state`
- `aither_state`
- `deployed_sha`
- `progress_current`
- `progress_total`

All remain optional sanitized scalar fields. Do not publish prompts, command text, stdout/stderr, file contents, secret values, tokens or credentials.

### 5. Systemd runner accuracy
Update `.agent/systemd_runner.py` so final live status uses the actual `task_id` and `executor` returned by the host runner summary rather than retaining a stale pre-fetch task id.

For the initial poll, it is acceptable to omit task id/executor until the current task is synchronized. Do not intentionally publish a known stale task id.

### 6. Summary
Extend host-runner result summaries with the selected executor so the caller and live publisher can report it.

### 7. Tests
Update tests to prove at least:
- task without `executor` fails validation;
- invalid executor fails validation;
- exact existing Codex argv remains correct;
- Hermes argv is an argv list, contains `-z`, fixed prompt, and no shell use;
- environment can pin Hermes executable path;
- dispatcher selects Codex and Hermes correctly;
- execution summary reports executor;
- live sanitizer accepts the new safe scalar fields;
- live sanitizer still rejects/arbitrarily omits unapproved prompt/output/secret-like fields;
- existing scope, tamper, rollback, idempotence, clean-worktree and push tests still pass.

## Hard prohibitions
- DO NOT modify `.agent/CURRENT_TASK.json` or `.agent/CURRENT_TASK.md`.
- DO NOT modify application code or manifests.
- DO NOT run Hermes against Aither in this task.
- DO NOT invoke Telegram.
- DO NOT run Kubernetes/deployment/database operations.
- DO NOT read or expose secrets.
- DO NOT install packages.
- DO NOT change systemd units or restart services.
- DO NOT expand allowed paths.

## Acceptance
Return `PASS` only if all required validation commands pass and only allowed `.agent` paths changed.
Do not declare Architect acceptance. STOP after this atomic task.
