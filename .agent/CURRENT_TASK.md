# TASK: CODEX-HARNESS-S1-R1 — FIX PR GATE AND ESTABLISH REPOSITORY TASK HANDOFF

## MODE
SOURCE GOVERNANCE CORRECTION ONLY

## Purpose
Correct the pull-request behavior of the Agent Gates harness and establish `.agent/CURRENT_TASK.md` as the human-readable task payload that Codex reads directly from GitHub/repository state.

## Baseline
Accepted source before Architect task handoff:
`40e6c7b346026a3b3305bc9ecb7b1d4618fff330`

Branch: `aither-v2`

Codex must first `git fetch origin` and fast-forward its local `aither-v2` to the current remote task-handoff commit. Local worktree must be clean before execution.

## Allowed implementation files
- `.agent/validate_task_scope.py`
- `.github/workflows/agent-gates.yml`

Architect-managed task files are also expected to differ from the baseline and must remain unchanged by Codex:
- `.agent/CURRENT_TASK.json`
- `.agent/CURRENT_TASK.md`

No other paths may change.

## Required correction

### 1. Pull-request branch semantics
The validator must continue to require `task.branch == aither-v2` locally and on push runs.

For GitHub Actions `pull_request` runs, it must not require `git branch --show-current` to equal `aither-v2`, because checkout may be detached or use a source branch.

Use GitHub Actions environment safely:
- when `GITHUB_EVENT_NAME=pull_request`, the authorized target branch is `GITHUB_BASE_REF`;
- require `GITHUB_BASE_REF == task.branch`;
- do not treat detached HEAD as a failure in that case;
- outside pull_request, retain the existing branch check.

No network/API calls from the validator.

### 2. Workflow checkout
For `pull_request`, checkout the PR head commit rather than relying on the synthetic merge commit. For push, checkout the pushed commit/branch normally.

Keep:
- `fetch-depth: 0`;
- `permissions: contents: read`;
- no secrets;
- no deployment;
- no third-party Python packages.

### 3. Validation evidence
Run locally:
- `python3 -m json.tool .agent/CURRENT_TASK.json >/dev/null`
- `python3 -m py_compile .agent/validate_task_scope.py`
- `python3 .agent/validate_task_scope.py`
- a simulated PR environment check using only environment variables and local git state; do not mutate repo;
- `git diff --check`

The local normal run must PASS.
The simulated PR branch logic must prove that target `aither-v2` is accepted even when `git branch --show-current` would not be used as the authorization source.

### 4. Commit discipline
Codex may create exactly one implementation commit and push it to `aither-v2`.
Recommended commit message:
`fix: make agent gate PR-aware`

Do not modify `.agent/CURRENT_TASK.json` or `.agent/CURRENT_TASK.md`.
Do not start another task.
Do not use kubectl, Docker, runtime, DB, secrets, package installation, deployment, amend, rebase, merge, or force push.

## Final report
Return:

TASK: CODEX-HARNESS-S1-R1
MODE: SOURCE GOVERNANCE CORRECTION ONLY
START HEAD: <full sha after pulling Architect task handoff>
NEW SHA: <full sha>
PARENT SHA: <full sha>
FILES CHANGED BY CODEX: 2
FILES:
.agent/validate_task_scope.py
.github/workflows/agent-gates.yml
LOCAL VALIDATOR: PASS/FAIL
SIMULATED PR TARGET BRANCH: PASS/FAIL
JSON VALIDATION: PASS/FAIL
PY_COMPILE: PASS/FAIL
GIT DIFF CHECK: PASS/FAIL
KUBERNETES ACCESSED: NO
DEPLOYMENT: NONE
DB CHANGES: NONE
RUNTIME CHANGES: NONE
SECRET ACCESS: NONE
NEW COMMIT: YES/NO
PUSH: PASS/FAIL
WORKTREE AFTER: clean/dirty
RESULT: PASS/FAIL/BLOCKED
STOP

Codex must not declare PASSED or CONNECTOR VERIFIED.
