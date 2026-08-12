# TASK: CODEX-HARNESS-S2-B1 — IMPLEMENT GOVERNED REAL CODEX EXECUTION PATH

## MODE
SOURCE GOVERNANCE EXECUTION PATH IMPLEMENTATION ONLY

## Purpose
Extend the accepted S2-A host runner with a real Codex execution path that can be used in the next canary stage. This task implements and unit-tests the path only. It MUST NOT perform a real `codex exec` during S2-B1.

Accepted baseline:
`62bc5880ab9622a1c6b1afd3ae1450a7d5e95bc1`

Branch: `aither-v2`

The launch HEAD may be a descendant of baseline because Architect publishes this task after baseline. `HEAD != baseline` is not a blocker. Require baseline ancestor success. The committed paths `baseline..START_HEAD` may contain only `.agent/CURRENT_TASK.json` and `.agent/CURRENT_TASK.md`.

## Files Codex may modify
- `.agent/host_task_runner.py`
- `.agent/tests/test_host_task_runner.py`

Do not modify Architect-managed task files.

## New capability
Add and require a boolean task capability:

`agent_exec`

Semantics:
- `agent_exec=false` MUST prohibit a real Codex execution path fail-closed.
- `agent_exec=true` permits the runner to invoke the fixed non-interactive Codex command only after all preflight checks pass.
- S2-B1 itself has `agent_exec=false`, therefore no real Codex execution is authorized in this task.

Do not weaken any existing capability checks.

## Required real execution design
Implement a testable execution function/path using dependency-injected command execution.

Preflight order must include:
1. acquire inter-process lock in Git metadata;
2. load and validate ACTIVE task;
3. require expected branch;
4. require clean worktree;
5. capture launch HEAD;
6. verify baseline exists and is ancestor of launch HEAD;
7. reject committed handoff paths outside Architect task-control paths;
8. require `agent_exec=true` before invoking Codex.

Codex invocation must use exactly the existing fixed argv:

`codex --ask-for-approval never --sandbox workspace-write exec <FIXED_PROMPT>`

No `shell=True` and no shell interpolation.

After Codex returns successfully:
1. enumerate exact changed worktree files with `git status --porcelain=v1 -z --untracked-files=all`;
2. reject every changed path outside task `allowed_paths`;
3. additionally reject any uncommitted modification to Architect-managed paths `.agent/CURRENT_TASK.json` or `.agent/CURRENT_TASK.md` as executor tampering, even though those paths are present in the handoff allowlist;
4. derive implementation paths eligible for a future host-side stage/commit;
5. run no Git mutation in S2-B1;
6. return deterministic machine-readable PASS/BLOCKED summary including task id, start head, changed paths, implementation paths and result.

If Codex exits non-zero, subprocess execution fails, branch/baseline/scope checks fail, or Architect-managed task files are modified: fail closed / BLOCKED and do not attempt any later action.

## CLI design
Retain `--dry-run`.

Add a separate explicit real-execution CLI mode, e.g. `--execute-codex`, mutually exclusive with `--dry-run`. The real mode must still honor `agent_exec` and all preflight checks. Tests must use injected/fake execution; do not invoke the real mode against Codex in S2-B1.

No fetch/pull/commit/push implementation is authorized yet.

## Tests required
Retain all existing 16 tests and add tests proving at minimum:

1. `agent_exec` is required and must be boolean;
2. `agent_exec=false` blocks execution before Codex command invocation;
3. `agent_exec=true` invokes exactly the fixed Codex argv after successful preflight using a fake runner;
4. unauthorized changed path after fake Codex execution blocks;
5. Architect-managed task file modification after fake Codex execution blocks;
6. authorized implementation path after fake Codex execution is returned as implementation path;
7. non-zero/failing fake Codex execution blocks;
8. real-execution summary is deterministic and contains task id, launch HEAD, changed paths, implementation paths and result;
9. `--dry-run` behavior remains non-executing;
10. existing default lock and `--untracked-files=all` protections remain covered.

Use Python standard library and `unittest` only. No network calls.

## Required validation

```bash
python3 -m json.tool .agent/CURRENT_TASK.json >/dev/null
python3 -m py_compile .agent/host_task_runner.py .agent/tests/test_host_task_runner.py
python3 .agent/tests/test_host_task_runner.py
python3 .agent/validate_task_scope.py
git diff --check
```

Do NOT run `--execute-codex` in S2-B1.

## Prohibited
- real `codex exec` in S2-B1
- git fetch/pull/commit/push from inside Codex
- staging/commit/push
- network calls
- root/sudo
- Kubernetes/kubectl
- Docker
- deployment
- DB/runtime mutation
- secret access
- package installation
- application code changes
- systemd/timers/cron
- autonomous next task

## Final report
TASK: CODEX-HARNESS-S2-B1
MODE: SOURCE GOVERNANCE EXECUTION PATH IMPLEMENTATION ONLY
START HEAD: <full SHA>
BASELINE: 62bc5880ab9622a1c6b1afd3ae1450a7d5e95bc1
BASELINE ANCESTOR CHECK: PASS/FAIL
COMMITTED PATHS BASELINE..START: <paths>
FILES CHANGED BY CODEX: <count>
FILES: <paths>
JSON VALIDATION: PASS/FAIL
PY_COMPILE: PASS/FAIL
UNIT TESTS: PASS/FAIL + test count
SCOPE VALIDATOR: PASS/FAIL
GIT DIFF CHECK: PASS/FAIL
AGENT_EXEC FALSE BLOCK TEST: PASS/FAIL
FAKE CODEX EXEC PATH TESTS: PASS/FAIL
ARCHITECT PATH TAMPER TEST: PASS/FAIL
REAL CODEX EXEC: NOT ATTEMPTED
GIT FETCH/PULL: NOT ATTEMPTED
NEW COMMIT: NO
PUSH: NOT ATTEMPTED
KUBERNETES ACCESSED: NO
DEPLOYMENT: NONE
DB CHANGES: NONE
RUNTIME CHANGES: NONE
SECRET ACCESS: NONE
WORKTREE AFTER: clean/dirty
RESULT: PASS/FAIL/BLOCKED
STOP

Do not declare PASSED or CONNECTOR VERIFIED.
