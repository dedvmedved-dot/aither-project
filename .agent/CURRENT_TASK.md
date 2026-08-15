# TASK: HERMES-INTEGRATION-H1-R4-R1-GOVERNANCE-PROTOCOL-CORRECTION

## Goal

Correct two remaining acceptance blockers found during independent Architect audit of commit `bf5ce3c9a5a59d2cb600b4d54aba985723dc35cb`:

1. `.agent/validate_task_scope.py` incorrectly treats Architect-managed task-control handoff files (`.agent/CURRENT_TASK.json`, `.agent/CURRENT_TASK.md`) as unauthorized implementation changes when they appear in the baseline-to-HEAD range.
2. The new Hermes bridge client currently uses `FIXED_SIGNAL = b"RUN\n"`; independently confirm the actual H2 executor framing semantics from the installed root executor source and align the client/tests to the exact accepted protocol without invoking a real Hermes execution.

This is a manual Hermes correction task. Do not invoke Codex or a real H2 RUN.

## Confirmed repository state

- Branch: `aither-v2`
- Baseline: `bf5ce3c9a5a59d2cb600b4d54aba985723dc35cb`
- H1-R4 implementation commit is present and pushed.
- H1-R4 is NOT Architect accepted yet.
- `aither-codex-runner.timer` must remain disabled.
- Existing Telegram Hermes Gateway must remain active and unrestarted.

## Required correction 1 — validator governance semantics

Update `.agent/validate_task_scope.py` so repository scope validation distinguishes:

- Architect-managed task-control handoff paths:
  - `.agent/CURRENT_TASK.json`
  - `.agent/CURRENT_TASK.md`
- executor implementation paths from `allowed_paths`.

The validator MUST:

- still require branch/baseline/task structure checks;
- accept Architect handoff files in the committed baseline-to-HEAD range even when they are not in `allowed_paths`;
- continue to reject any other changed path outside `allowed_paths`;
- continue to include untracked files in scope validation;
- fail closed;
- not weaken implementation allowlisting.

Use a fixed constant such as `ARCHITECT_PATHS` rather than dynamically trusting arbitrary task fields.

Add `.agent/tests/test_validate_task_scope.py` covering at least:

- only Architect handoff paths + allowed implementation paths => PASS;
- unexpected committed path => FAIL;
- unexpected untracked path => FAIL;
- duplicate/malformed task allowlist still fails;
- Architect paths do NOT become generally writable implementation paths.

## Required correction 2 — H2 protocol framing audit

Read-only inspect the installed root executor source:

`/usr/local/sbin/aither-hermes-root-exec`

Do not execute it.
Do not connect to `/run/aither-hermes/execute.sock` with `RUN`.
Do not print secrets or unrelated file contents.

Determine exactly how it parses socket input and whether the accepted wire form is:

- `RUN`
- `RUN\n`
- or another fixed framing that is explicitly normalized before exact comparison.

Then align `.agent/hermes_observer.py` and `.agent/tests/test_hermes_observer.py` to the factual protocol.

Requirements remain:

- fixed non-user-controlled signal only;
- no direct Hermes CLI;
- no arbitrary prompt/command;
- bounded response;
- timeout;
- fail closed on `BLOCKED_*` / `FAIL`;
- no shell/eval/exec.

If `RUN\n` is already exactly compatible because the executor strips line framing before comparing literal `RUN`, document that in the final report and no code change is required for framing.

If the current client framing is incompatible, correct it and update tests.

## Hard prohibitions

- DO NOT modify `.agent/CURRENT_TASK.json` or `.agent/CURRENT_TASK.md`.
- DO NOT modify any path outside the allowed paths in CURRENT_TASK.json.
- DO NOT run Codex.
- DO NOT invoke real H2 bridge RUN.
- DO NOT start another Hermes.
- DO NOT restart/reconfigure Telegram Gateway.
- DO NOT enable/start `aither-codex-runner.timer`.
- DO NOT modify systemd unit files.
- DO NOT touch application/runtime/Kubernetes/database.
- DO NOT read or expose secrets.
- DO NOT install packages or modify sudoers.

## Required validation

Run every command from CURRENT_TASK.json. All must PASS, including:

```bash
python3 .agent/validate_task_scope.py
```

No waiver is allowed for the scope validator in this correction task.

## Commit / push

If and only if all validations pass:

- exactly one implementation commit;
- commit message: `fix: align task scope validation with architect handoff`;
- push to `aither-v2`;
- clean worktree after push.

## Required final report

```text
TASK: HERMES-INTEGRATION-H1-R4-R1-GOVERNANCE-PROTOCOL-CORRECTION
BASELINE_SHA:
START_HEAD:
WORKTREE_BEFORE:

VALIDATOR_ARCHITECT_PATHS_FIXED:
VALIDATOR_ALLOWED_IMPLEMENTATION_PATHS_PRESERVED:
VALIDATOR_UNEXPECTED_COMMITTED_FAILS:
VALIDATOR_UNTRACKED_FAILS:
VALIDATOR_TESTS:
TASK_SCOPE_VALIDATOR:

ROOT_EXECUTOR_READ_ONLY_INSPECTED:
ROOT_EXECUTOR_PROTOCOL_PARSE:
ROOT_EXECUTOR_LITERAL_COMPARE:
CLIENT_SIGNAL_BEFORE:
CLIENT_SIGNAL_AFTER:
PROTOCOL_COMPATIBLE:
REAL_H2_RUN_INVOKED: NO
REAL_HERMES_EXECUTED: NO

PY_COMPILE:
HERMES_OBSERVER_TESTS:
GIT_DIFF_CHECK:

CHANGED_PATHS:
OUTSIDE_ALLOWLIST:
CURRENT_TASK_FILES_MODIFIED: NO
APPLICATION_RUNTIME_MODIFIED: NO
SYSTEMD_UNIT_FILES_MODIFIED: NO
CODEX_EXECUTED: NO
TELEGRAM_GATEWAY_RESTARTED: NO
SECRETS_EXPOSED: NO

RESULT_COMMIT:
PUSH:
WORKTREE_AFTER:
RESULT: PASS|FAIL|BLOCKED
STOP
```

Return PASS only if every required validation passes. Do not declare Architect acceptance.

STOP.
