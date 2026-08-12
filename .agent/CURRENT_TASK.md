# TASK: CODEX-HARNESS-S1-R3 — CI BRANCH-AWARE VALIDATOR WITHOUT GIT MUTATION

## MODE
SOURCE GOVERNANCE CORRECTION ONLY

## Execution model for this task
Git metadata is read-only inside Codex `workspace-write` sandbox by design. Therefore this task deliberately forbids `git fetch`, `git commit`, and `git push` from inside Codex.

The host/operator must update the repository to the current Architect task commit BEFORE launching Codex. Codex then only edits the explicitly allowed implementation file and runs local validation. Commit/push will be performed outside Codex after its STOP report.

## Baseline
`a87ec01a9ca7cc295a1e2a951c6515809cc0bb44`

Branch: `aither-v2`

## Architect-managed files
Do not modify:
- `.agent/CURRENT_TASK.json`
- `.agent/CURRENT_TASK.md`

## Only implementation file Codex may modify
- `.agent/validate_task_scope.py`

No other implementation path may change.

## Required correction
Branch authorization must not depend on attached HEAD inside GitHub Actions.

Implement this precedence:

1. If `GITHUB_ACTIONS=true` and `GITHUB_EVENT_NAME=pull_request`:
   - authorized branch source = `GITHUB_BASE_REF`;
   - require it equals `task.branch`.

2. Else if `GITHUB_ACTIONS=true`:
   - authorized branch source = `GITHUB_REF_NAME`;
   - require it equals `task.branch`.

3. Else, local execution outside GitHub Actions:
   - authorized branch source = `git branch --show-current`;
   - require it equals `task.branch`.

Fail closed if a required GitHub environment variable is empty or missing.

No network/API calls. No writes outside the allowed implementation file. No shell=True.
Do not modify `.github/workflows/agent-gates.yml`.

## Required validation
Run:

```bash
python3 -m json.tool .agent/CURRENT_TASK.json >/dev/null
python3 -m py_compile .agent/validate_task_scope.py
python3 .agent/validate_task_scope.py
GITHUB_ACTIONS=true GITHUB_EVENT_NAME=push GITHUB_REF_NAME=aither-v2 python3 .agent/validate_task_scope.py
GITHUB_ACTIONS=true GITHUB_EVENT_NAME=pull_request GITHUB_BASE_REF=aither-v2 python3 .agent/validate_task_scope.py
git diff --check
```

Also run one negative test:

```bash
GITHUB_ACTIONS=true GITHUB_EVENT_NAME=push GITHUB_REF_NAME=main python3 .agent/validate_task_scope.py
```

The negative test must fail non-zero with branch mismatch. That expected failure is PASS for the negative test.

## Prohibited
- git fetch / pull / commit / push inside Codex
- Kubernetes / kubectl
- Docker
- deployment
- DB/runtime mutation
- secret access
- package installation
- application code changes
- autonomous next task

## Final report

TASK: CODEX-HARNESS-S1-R3
MODE: SOURCE GOVERNANCE CORRECTION ONLY
START HEAD: <full SHA visible at launch>
FILES CHANGED BY CODEX: 1
FILES:
.agent/validate_task_scope.py
LOCAL VALIDATOR: PASS/FAIL
SIMULATED PUSH: PASS/FAIL
SIMULATED PR: PASS/FAIL
NEGATIVE WRONG-BRANCH TEST: PASS/FAIL
JSON VALIDATION: PASS/FAIL
PY_COMPILE: PASS/FAIL
GIT DIFF CHECK: PASS/FAIL
KUBERNETES ACCESSED: NO
DEPLOYMENT: NONE
DB CHANGES: NONE
RUNTIME CHANGES: NONE
SECRET ACCESS: NONE
GIT FETCH: NOT ATTEMPTED
NEW COMMIT: NO
PUSH: NOT ATTEMPTED
WORKTREE AFTER: clean/dirty
RESULT: PASS/FAIL/BLOCKED
STOP

Do not declare PASSED or CONNECTOR VERIFIED.
