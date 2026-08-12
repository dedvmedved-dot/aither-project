# TASK: CODEX-HARNESS-S2-AUTONOMOUS-SOURCE-PUBLISH

## MODE
ARCHITECT MANAGEMENT SOURCE PUBLICATION

This is an Architect-owned publication commit for the autonomous host supervisor. It is not an executor task and MUST NOT be executed by Codex.

The published management layer contains:
- fail-closed host supervisor;
- executor/host permission separation;
- fixed non-interactive Codex invocation in workspace-write;
- exact worktree path enumeration;
- Architect task-control tamper protection;
- validation before staging;
- fast-forward-only sync;
- remote race check before host commit;
- non-force push only;
- rollback of failed executor output;
- Git-metadata flock and success fingerprint state;
- systemd oneshot + timer installation;
- integration tests using an isolated local bare Git remote.

The next Architect commit will publish the first autonomous canary task with this commit as its baseline.

RESULT ownership: only Architect may declare PASSED / CONNECTOR VERIFIED.
