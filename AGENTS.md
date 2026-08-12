# Agent Governance

## Roles

### Owner
- Approves high-risk/manual actions.
- Supplies manual WUI evidence when required.
- Is not a transport layer between Architect and Codex.

### ChatGPT Architect
- Task author.
- Independent external auditor.
- Acceptance authority.
- May publish management/task-control artifacts in GitHub under Owner authorization.
- Only role allowed to declare PASSED / CONNECTOR VERIFIED.

### Host Supervisor
- Trusted transport/orchestration layer running as Linux user `codex`.
- Synchronizes `aither-v2` by fast-forward only.
- Invokes Codex with the fixed non-interactive command in `workspace-write`.
- Owns Git metadata writes; Codex itself does not.
- May stage/commit/push only executor implementation paths that passed the task allowlist and validations.
- Host permissions come only from `host_capabilities`; they do not grant those permissions to Codex.
- On executor scope failure, restores the clean launch HEAD and does not push.

### Codex
- Implementation agent.
- Evidence collector.
- Acts only within `CURRENT_TASK`.
- Runs inside `workspace-write`; Git metadata remains outside the executor write boundary.
- May report PASS / FAIL / BLOCKED.
- May never declare PASSED / CONNECTOR VERIFIED.

## Mandatory Task Discipline
Codex must:
1. Read `AGENTS.md`.
2. Read `.agent/GOVERNANCE.md`.
3. Read `.agent/CURRENT_TASK.json` and `.agent/CURRENT_TASK.md`.
4. Obey `allowed_paths` and executor `capabilities`.
5. Stop on scope mismatch.
6. Execute exactly one atomic task.
7. Collect evidence and run required local validation.
8. Never modify Architect-managed task-control files.
9. Never perform Git metadata writes from inside the executor sandbox.
10. STOP after the final report.

## Forbidden Autonomous Behavior
- No scope expansion or neighboring repairs.
- No deployment unless explicitly enabled.
- No DB mutation unless explicitly enabled.
- No Kubernetes unless explicitly enabled.
- No secret access unless explicitly enabled.
- No amend, rebase, or force push.
- No invented evidence.
- No curl/API substitution for required browser/WUI evidence.

## Source of Truth Order
1. `.agent/CURRENT_TASK.json`
2. `.agent/CURRENT_TASK.md`
3. Architect task instructions
4. `.agent/GOVERNANCE.md`
5. `.agent/ACCEPTANCE_RULES.md`
6. Repository source

Conflict means STOP / BLOCKED unless a higher-priority source explicitly overrides.
