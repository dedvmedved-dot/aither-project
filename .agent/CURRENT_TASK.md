# TASK: HERMES-INTEGRATION-H1-R4-R2-COMMITTED-SCOPE-VALIDATION

## Goal

Fix one remaining acceptance defect in `.agent/validate_task_scope.py` discovered by independent Architect audit of commit `329f56943342f900495fb22591351998537138dd`.

The current validator incorrectly treats committed implementation files in `baseline..HEAD` as unauthorized unless they are Architect task-control paths. That means a legitimate result commit containing files from `allowed_paths` can fail validation after commit.

This task must correct only that behavior and add a regression test for the committed-result state.

## Confirmed repository state

- Branch: `aither-v2`
- Baseline: `329f56943342f900495fb22591351998537138dd`
- Executor: `hermes`
- H1-R4-R1 is NOT Architect accepted.
- `aither-codex-runner.timer` must remain disabled.
- Aither/Kubernetes/runtime must not be touched.

## Exact defect

Current logic is effectively:

```python
{path for path in committed if path not in ARCHITECT_PATHS}
```

This rejects a legitimate committed implementation path even when that path is present in `allowed_paths`.

Correct semantics:

- committed `baseline..HEAD` path is authorized if it is either:
  - in fixed `ARCHITECT_PATHS`, OR
  - in current task `allowed_paths`;
- worktree and untracked paths are authorized ONLY if in `allowed_paths`;
- Architect task-control paths must NOT become writable implementation paths merely because they are architect paths;
- all other paths fail closed.

## Required implementation

Modify only:

- `.agent/validate_task_scope.py`
- `.agent/tests/test_validate_task_scope.py`

The core committed-path rule must be equivalent to:

```python
path in ARCHITECT_PATHS or path in allowed
```

Do not dynamically trust any extra task field as an Architect path source.

## Mandatory regression tests

Add/adjust tests proving at least:

1. `committed={CURRENT_TASK.json, CURRENT_TASK.md, allowed_impl.py}` with `allowed={allowed_impl.py}` => PASS.
2. committed allowed implementation path alone => PASS.
3. unexpected committed path => FAIL.
4. Architect handoff paths in committed range => PASS even if not in allowed_paths.
5. Architect path in worktree => FAIL unless explicitly in allowed_paths; however do NOT add Architect paths to this task's allowed_paths.
6. unexpected untracked path => FAIL.
7. allowed worktree implementation path => PASS.
8. duplicate/malformed allowlist still fails.

## Validation order

### Before commit

Run all commands from `CURRENT_TASK.json`.

They must pass.

### Commit

If and only if pre-commit validations pass:

- create exactly one implementation commit;
- commit message exactly:
  `fix: allow committed task-scoped implementation paths`

### CRITICAL post-commit validation

Before push, with worktree clean and HEAD now containing the result commit, run again:

```bash
python3 .agent/validate_task_scope.py
```

This post-commit run is mandatory and is the key acceptance check.

It must return:

```text
UNAUTHORIZED_PATHS=0
RESULT=PASS
```

Also rerun:

```bash
PYTHONPATH=.agent python3 .agent/tests/test_validate_task_scope.py
git diff --check HEAD^..HEAD
```

If post-commit validator fails:

- DO NOT amend repeatedly;
- DO NOT push;
- return `FAIL` and STOP.

If it passes, push fast-forward to `aither-v2`.

## Hard prohibitions

- DO NOT modify `.agent/CURRENT_TASK.json` or `.agent/CURRENT_TASK.md`.
- DO NOT modify any path outside the two allowed implementation paths.
- DO NOT run Codex.
- DO NOT invoke H2 bridge.
- DO NOT execute Hermes recursively.
- DO NOT enable/start runner timer/service.
- DO NOT touch application/runtime/Kubernetes/database.
- DO NOT change systemd units.
- DO NOT read/expose secrets.
- DO NOT install packages or modify sudoers.

## Required final report

```text
TASK: HERMES-INTEGRATION-H1-R4-R2-COMMITTED-SCOPE-VALIDATION
BASELINE_SHA:
START_HEAD:
WORKTREE_BEFORE:

COMMITTED_ARCHITECT_PLUS_ALLOWED_IMPL_PASS:
COMMITTED_ALLOWED_IMPL_PASS:
UNEXPECTED_COMMITTED_FAILS:
ARCHITECT_WORKTREE_FAILS:
UNEXPECTED_UNTRACKED_FAILS:
VALIDATOR_TESTS_PRE_COMMIT:
TASK_SCOPE_VALIDATOR_PRE_COMMIT:

CHANGED_PATHS:
OUTSIDE_ALLOWLIST:
CURRENT_TASK_FILES_MODIFIED: NO
APPLICATION_RUNTIME_MODIFIED: NO
CODEX_EXECUTED: NO
REAL_HERMES_EXECUTED: NO
SECRETS_EXPOSED: NO

RESULT_COMMIT:
POST_COMMIT_WORKTREE_CLEAN:
TASK_SCOPE_VALIDATOR_POST_COMMIT:
POST_COMMIT_UNAUTHORIZED_PATHS:
VALIDATOR_TESTS_POST_COMMIT:
GIT_DIFF_CHECK_POST_COMMIT:
PUSH:
REMOTE_HEAD:
WORKTREE_AFTER:

RESULT: PASS|FAIL|BLOCKED
STOP
```

PASS is allowed only when the post-commit validator passes on the actual result HEAD before push.

STOP.
