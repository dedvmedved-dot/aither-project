# TASK: HERMES-INTEGRATION-H4-R1-GOVERNANCE-BEFORE-ELIGIBILITY

## Goal

Correct one acceptance defect found by independent Architect audit of commit `e83cc345fffedfe1a731a76e864bd3242fc8a1d6`.

The H4 retry governor correctly preserves fast sync and suppresses repeated failed executor attempts, but it currently performs `IDLE` / `SUPPRESSED` eligibility returns before baseline and committed-handoff governance validation.

That ordering is not acceptable because a newly fetched remote commit that does not change the task fingerprint can be fast-forwarded locally and then hidden behind `SUPPRESSED` or `IDLE` without running `verify_baseline_ancestor()` / `committed_handoff_paths()`.

This correction must preserve all H4 retry semantics while enforcing governance before any eligibility-based early return.

## Confirmed defect

Current flow after sync is effectively:

```text
sync -> load task -> fingerprint/state -> IDLE/SUPPRESSED return -> governance
```

Required flow:

```text
sync
 -> load synchronized task
 -> branch validation
 -> baseline ancestor validation
 -> committed handoff path validation
 -> fingerprint/state
 -> IDLE / SUPPRESSED / execute eligibility
```

No synced repository state may bypass baseline/handoff governance merely because the task fingerprint matches a prior PASS/BLOCKED state.

## Required implementation

Modify only:

- `.agent/host_task_runner.py`
- `.agent/tests/test_host_task_runner.py`

Move or restructure the eligibility checks so both:

- successful-fingerprint `IDLE`, and
- failed-fingerprint `SUPPRESSED`

occur only after all synchronized Git governance checks for the current HEAD have passed.

Do not change Codex/Hermes dispatcher behavior.
Do not change retry-state field names or live/systemd mappings unless absolutely necessary; preferred correction is limited to host runner ordering and tests.

## Mandatory regression tests

Tests must prove at least:

1. Same BLOCKED fingerprint + unchanged governed HEAD => `SUPPRESSED`, executor not called.
2. Same PASS fingerprint + unchanged governed HEAD => `IDLE`, executor not called.
3. Suppressed poll still performs fetch/sync.
4. If fetch/sync advances HEAD with an unexpected committed path while task fingerprint is unchanged, runner MUST NOT return `SUPPRESSED`; it must fail governance before executor eligibility.
5. The same scenario for a previously successful fingerprint MUST NOT return `IDLE`; governance must fail first.
6. A valid Architect task-control handoff that changes fingerprint remains eligible immediately after governance passes.
7. Existing BLOCKED state recording remains correct.
8. Existing `SUPPRESSED` CLI exit-0 behavior remains unchanged.
9. Existing Codex/Hermes dispatcher tests remain unchanged/passing.
10. No real executor is invoked during this implementation task.

Important: remove/replace any test that treats an arbitrary remote `extra.txt` commit as acceptable merely because suppression occurs. That behavior is the defect.

## Required validation

Run every command from CURRENT_TASK.json. All must PASS.

At minimum:

```bash
python3 -m py_compile .agent/host_task_runner.py .agent/tests/test_host_task_runner.py
PYTHONPATH=.agent python3 .agent/tests/test_host_task_runner.py
PYTHONPATH=.agent python3 .agent/tests/test_live_observability.py
python3 .agent/validate_task_scope.py
git diff --check
```

## Hard prohibitions

DO NOT:

- modify `.agent/CURRENT_TASK.json` or `.agent/CURRENT_TASK.md` locally;
- modify systemd timer/service files;
- enable/start timer;
- run Codex;
- invoke H2 RUN;
- spawn Hermes recursively;
- modify root executor;
- restart/reconfigure Telegram Gateway;
- touch Aither runtime/Kubernetes/database;
- install packages;
- modify sudoers;
- read/expose secrets;
- modify paths outside CURRENT_TASK.json allowed_paths.

## Commit / push

If and only if all validations pass:

- exactly one implementation commit;
- commit message exactly: `fix: enforce governance before retry suppression`;
- push fast-forward to `aither-v2`;
- clean worktree after push.

## Required final report

```text
TASK: HERMES-INTEGRATION-H4-R1-GOVERNANCE-BEFORE-ELIGIBILITY
BASELINE_SHA:
START_HEAD:
WORKTREE_BEFORE:

SYNC_BEFORE_GOVERNANCE:
BRANCH_CHECK_BEFORE_ELIGIBILITY:
BASELINE_CHECK_BEFORE_ELIGIBILITY:
COMMITTED_HANDOFF_CHECK_BEFORE_ELIGIBILITY:
IDLE_AFTER_GOVERNANCE_ONLY:
SUPPRESSED_AFTER_GOVERNANCE_ONLY:

BLOCKED_SAME_FINGERPRINT_SUPPRESSED:
PASS_SAME_FINGERPRINT_IDLE:
SUPPRESSED_STILL_FETCHES:
UNEXPECTED_REMOTE_COMMIT_BLOCKS_BEFORE_SUPPRESSION:
UNEXPECTED_REMOTE_COMMIT_BLOCKS_BEFORE_IDLE:
NEW_VALID_TASK_FINGERPRINT_UNLOCKS:
EXECUTOR_NOT_CALLED_DURING_SUPPRESSION:

CODEX_DISPATCH_UNCHANGED:
HERMES_DISPATCH_UNCHANGED:
REAL_CODEX_EXECUTED: NO
REAL_H2_RUN_INVOKED: NO
REAL_HERMES_EXECUTED: NO

PY_COMPILE:
HOST_RUNNER_TESTS:
LIVE_OBSERVABILITY_TESTS:
TASK_SCOPE_VALIDATOR:
GIT_DIFF_CHECK:

CHANGED_PATHS:
OUTSIDE_ALLOWLIST:
CURRENT_TASK_FILES_MODIFIED: NO
TIMER_FILES_MODIFIED: NO
TIMER_ENABLED: disabled
TIMER_ACTIVE: inactive
ROOT_EXECUTOR_MODIFIED: NO
TELEGRAM_GATEWAY_RESTARTED: NO
AITHER_RUNTIME_MODIFIED: NO
KUBERNETES_TOUCHED: NO
SECRETS_EXPOSED: NO

RESULT_COMMIT:
PUSH:
REMOTE_HEAD:
WORKTREE_AFTER:
RESULT: PASS|FAIL|BLOCKED
STOP
```

PASS only if governance is proven to run before both IDLE and SUPPRESSED eligibility returns and exactly one allowed implementation commit is pushed.

Do not declare Architect acceptance.

STOP.
