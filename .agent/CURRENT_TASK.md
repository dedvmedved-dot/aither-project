# TASK: CODEX-HARNESS-S2-A — SAFE HOST TASK RUNNER IMPLEMENTATION

## MODE
SOURCE GOVERNANCE LAUNCHER IMPLEMENTATION ONLY

## Purpose
Implement the first source-only version of the host-side Codex task runner. This stage proves orchestration logic only. It MUST NOT perform a real Codex run, real fetch/pull, commit, push, deployment, Kubernetes access, secret access, or runtime mutation during this task.

The accepted source baseline is:
`13cdd1301b87d7274bdbbf4c0973f6d8a0c91f4c`

Branch: `aither-v2`

The launch HEAD is expected to be a descendant of the baseline because Architect publishes this task after the accepted baseline. `HEAD != baseline` is NOT a blocker. Verify with `git merge-base --is-ancestor <baseline> HEAD` and require success. The committed diff `baseline..START_HEAD` may contain only Architect-managed task-control paths. For this task, the final net diff from baseline to START_HEAD must be limited to `.agent/CURRENT_TASK.json` and `.agent/CURRENT_TASK.md`.

## Files Codex may create/modify
- `.agent/host_task_runner.py`
- `.agent/tests/test_host_task_runner.py`

Do not modify Architect-managed task files.

## Required runner design
Use Python 3 standard library only.

Implement a deterministic host-side runner with a CLI. In this S2-A stage it must support a safe simulation/dry-run mode and expose testable pure/helper functions. It must NOT execute real mutating Git or Codex commands in the tests.

Required responsibilities:

1. Resolve repository root and require expected branch from task JSON.
2. Load and validate `.agent/CURRENT_TASK.json` with required fields and types.
3. Fail closed if task status is not `ACTIVE`.
4. Require clean worktree before a future real run.
5. Verify `baseline_sha` exists and is ancestor of launch HEAD; do not require HEAD == baseline.
6. Compute committed paths between baseline and launch HEAD and reject paths outside Architect task-control allowlist for the handoff.
7. Build the exact non-interactive Codex argv without shell interpolation. The approval flag is global and must appear before `exec`:
   `codex --ask-for-approval never --sandbox workspace-write exec <prompt>`
   Do not use `shell=True`.
8. Use the fixed prompt:
   `Read AGENTS.md, .agent/CURRENT_TASK.json and .agent/CURRENT_TASK.md. Execute the current task exactly as authorized. Do not expand scope. Return the required final report and STOP.`
9. After a future Codex execution, enumerate changed worktree paths using Git porcelain output and reject every changed path not in task `allowed_paths`.
10. Separate Architect-managed paths from implementation paths and refuse to stage/commit Architect-managed task files as executor output.
11. Provide a function that derives implementation paths eligible for staging from changed paths and task data.
12. Enforce capability flags fail-closed: commit/push/network_git false must prohibit corresponding future runner action.
13. Generate a deterministic machine-readable summary (dict/JSON-ready) for PASS/FAIL/BLOCKED decisions.
14. Add an inter-process lock design using standard library only; tests may use a temporary lock path. No daemon/systemd in S2-A.
15. Never call kubectl, Docker, deployment commands, DB/runtime mutation, package managers, or secret-reading commands.

## Safety boundary for S2-A
The runner source MAY contain functions that would later call subprocess for Git/Codex, but S2-A tests must inject/mocking/stub command execution. The task itself must not invoke the runner in a mode that performs real fetch/pull/commit/push or real `codex exec`.

## Tests required
Create `.agent/tests/test_host_task_runner.py` using `unittest` only.

At minimum prove:
- valid ACTIVE task loads;
- non-ACTIVE task fails closed;
- baseline ancestor accepted and equality not required;
- unexpected committed handoff path rejected;
- exact Codex argv has `--ask-for-approval never` before `exec` and `--sandbox workspace-write`;
- no shell=True in command execution abstraction;
- changed path inside allowlist accepted;
- changed path outside allowlist rejected;
- Architect-managed task paths excluded from executor staging candidates;
- commit=false blocks commit action;
- push=false blocks push action;
- network_git=false blocks fetch/pull action;
- lock contention fails closed;
- deterministic summary contains task id, start head, changed paths and result.

## Required validation
Run only local non-mutating validation:

```bash
python3 -m json.tool .agent/CURRENT_TASK.json >/dev/null
python3 -m py_compile .agent/host_task_runner.py .agent/tests/test_host_task_runner.py
python3 -m unittest -v .agent.tests.test_host_task_runner
python3 .agent/validate_task_scope.py
git diff --check
```

If Python module discovery for `.agent.tests...` is unsuitable because `.agent` is not a package, run the test file directly with `python3 .agent/tests/test_host_task_runner.py` and report the exact command used. Do not add unrelated `__init__.py` unless required and authorized.

## Prohibited
- real `codex exec` invocation in S2-A
- git fetch/pull/commit/push from inside Codex
- staging or committing
- network calls
- root/sudo
- Kubernetes/kubectl
- Docker
- deployment
- DB/runtime changes
- secret access
- package installation
- application code changes
- systemd/timers/cron
- autonomous next task

## Final report
TASK: CODEX-HARNESS-S2-A
MODE: SOURCE GOVERNANCE LAUNCHER IMPLEMENTATION ONLY
START HEAD: <full SHA>
BASELINE: 13cdd1301b87d7274bdbbf4c0973f6d8a0c91f4c
BASELINE ANCESTOR CHECK: PASS/FAIL
COMMITTED PATHS BASELINE..START: <paths>
FILES CHANGED BY CODEX: <count>
FILES: <paths>
JSON VALIDATION: PASS/FAIL
PY_COMPILE: PASS/FAIL
UNIT TESTS: PASS/FAIL
SCOPE VALIDATOR: PASS/FAIL
GIT DIFF CHECK: PASS/FAIL
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
