# Agent Governance

## Roles

### Owner

- Approves high-risk/manual actions.
- Supplies manual WUI evidence when required.

### ChatGPT Architect

- Task author.
- Independent external auditor.
- Acceptance authority.
- Only role allowed to declare PASSED / CONNECTOR VERIFIED.

### Codex

- Implementation agent.
- Evidence collector.
- Acts only within `CURRENT_TASK`.
- May report PASS / FAIL / BLOCKED.
- May never declare PASSED / CONNECTOR VERIFIED.

## Mandatory Task Discipline

Codex must:

1. Read `AGENTS.md`.
2. Read `.agent/GOVERNANCE.md`.
3. Read `.agent/CURRENT_TASK.json`.
4. Verify branch, baseline SHA, and clean worktree.
5. Obey `allowed_paths` and capability flags.
6. Stop on scope mismatch.
7. Execute exactly one atomic task.
8. Collect evidence.
9. Run the scope validator before commit.
10. Create at most one implementation commit if authorized.
11. Push only if authorized.
12. STOP after the final report.

## Forbidden Autonomous Behavior

- No scope expansion.
- No neighboring repairs.
- No deployment unless explicitly enabled.
- No DB mutation unless explicitly enabled.
- No Kubernetes unless explicitly enabled.
- No secret access unless explicitly enabled.
- No amend, rebase, or force push.
- No invented evidence.
- No curl/API substitution for required browser/WUI evidence.

## Source of Truth Order

1. `CURRENT_TASK.json`
2. Architect task instructions
3. `GOVERNANCE.md`
4. `ACCEPTANCE_RULES.md`
5. Repository source

Conflict means STOP / BLOCKED unless a higher-priority source explicitly overrides.
