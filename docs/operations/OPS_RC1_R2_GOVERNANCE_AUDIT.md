# OPS-RC1 R2 — Governance Finalization Audit

**Task:** `AITHER-MVP-GOV-R2-FINALIZE-R1`
**Mode:** GOVERNANCE_FINALIZATION (repository/governance audit only — no runtime mutation)
**Executor:** Hermes (HERMES-INTEGRATION)
**Date:** 2026-08-18
**Branch:** `aither-v2`

This audit is read-only. It does not repeat OPS-RC1 implementation, does not touch
Kubernetes/runtime, and does not modify any governance code or task-control file.
The only worktree change produced by this audit is this file.

---

## A. R2 commit provenance

### A.1 HEAD / parent relationship

- Current local HEAD at audit time: `17bdcb55c85772ade2186632ee7e2b5c054e6f78`
  (`architect: publish R2 governance finalization`).
- R2 implementation commit: `e51f06b3d38906ac1c3c33a0c2bf1f8516f3b4c1`
  (`ops: close RC1 operations gate R2`).
- Parent of `e51f06b3`: `d850f55a18c0370ea3a0e196c5043b0fc0ba6981`
  (`architect: publish OPS-RC1-R2`).

Confirmed chain (chronological):

```
85345c4506bcdb54226e03b8e78a2a397612cf3f  architect: gate: atomically publish OPS-RC1 task control
63ad4ef91221aa32cfa3d1be6cdc770787a0a9a4  Aither Codex: ops: close RC1 operations gate
d850f55a18c0370ea3a0e196c5043b0fc0ba6981  architect: publish OPS-RC1-R2
e51f06b3d38906ac1c3c33a0c2bf1f8516f3b4c1  Aither Codex: ops: close RC1 operations gate R2
17bdcb55c85772ade2186632ee7e2b5c054e6f78  architect: publish R2 governance finalization
```

`e51f06b3` is exactly one commit ahead of the R2 Architect publication `d850f55`
(parent = `d850f55`), and `17bdcb5` is exactly one commit ahead of `e51f06b3`.

### A.2 Changed paths in `d850f55..e51f06b3`

`git diff --name-only d850f55a18c0370ea3a0e196c5043b0fc0ba6981..e51f06b3d38906ac1c3c33a0c2bf1f8516f3b4c1`:

```
ROADMAP-RECOVERY.md
docs/operations/OPS_RC1_R2_EVIDENCE.md
manifests/backups.yaml
manifests/network-policies.yaml
manifests/observability/alertmanager.yaml
manifests/observability/kube-state-metrics.yaml
manifests/observability/node-exporter.yaml
manifests/observability/prometheus.yaml
manifests/quotas.yaml
```

R2 `allowed_paths` (from the R2 task control published at `d850f55`) contained
14 exact paths. All 9 changed paths are a strict subset of that allowlist; no
path outside the R2 allowlist was committed. The remaining 5 allowlist paths
(`manifests/postgres.yaml`, `manifests/redis.yaml`, and the three
`docs/operations/*_GUIDE.md` files) were authorized but not changed, which is
allowed.

### A.3 Actor/path that created and pushed `e51f06b3`

`git show -s --format=...` for `e51f06b3`:

- author / committer: `Aither Codex <codex@aither.local>`
- commit timestamp: `2026-08-18 08:32:30 +0300`

The repository's `user.name`/`user.email` for user `codex` are exactly
`Aither Codex` / `codex@aither.local`, so the commit was authored through the
`codex` git identity.

Two independent facts prove the **host runner did NOT produce this commit**:

1. The commit contains **no** `.agent/EXECUTION_RESULT.json`. The host runner's
   `stage_commit_push` unconditionally stages `RESULT_PATH`
   (`sorted(set(implementation) | {RESULT_PATH})`), so any commit it makes
   always includes that file. Its absence here excludes the host runner path.
2. The host runner's own journal entry at `08:34:54` for this very execution
   reports `BLOCKED` with
   `remote moved during execution: expected d850f55..., got e51f06b3...` — i.e.
   the runner *detected* `e51f06b3` already on the remote and aborted before
   committing anything.

The R2 execution window is observable in systemd:

- `08:10:48` — `aither-codex-runner.service` poll started (synced to `d850f55`),
  spawned the executor via the H2 socket bridge (`aither-hermes-exec@15-3570599-1000.service`).
- `08:32:30` — burst of `runuser(uid=0 -> codex)` git sessions (4 sessions at
  the exact commit timestamp), consistent with `git add` + `git commit`
  (+ push) executed by the **root Hermes executor** via `runuser -u codex -- git ...`.
- `08:34:34` — `aither-hermes-exec@15` deactivated (executor finished, 53.8s CPU).
- `08:34:54` — host runner `stage_commit_push` fetched the remote, found
  `e51f06b3` ≠ start_head `d850f55`, and raised `remote moved during execution`.

Because `aither-hermes-exec@*.service` runs as `User=root` and the host runner
runs as `User=codex` (its git calls need no `runuser`), the `runuser -u codex`
git sessions at `08:32:30` originate from the root Hermes executor, not the host
runner. The local reflog confirms the same sequence:

```
e51f06b HEAD@{4}: commit: ops: close RC1 operations gate R2
d850f55 HEAD@{3}: reset: moving to d850f55...
d850f55 HEAD@{2}: reset: moving to d850f55...
e51f06b HEAD@{1}: merge origin/aither-v2: Fast-forward
```

**PROVENANCE: root Hermes executor self-commit/self-push** (HIGH confidence).
The executor authored and pushed `e51f06b3` through the `codex` git identity at
`08:32:30`, i.e. *during its own execution window and before the host runner
could publish its own result commit*. This is a `network_git=false` / governance
separation violation by the executor (executor must never perform git
commit/push). The attribution is high-confidence inference (reflog + runuser PAM
sessions + commit author + absent `RESULT_PATH`); the executor's exact command
stream is not directly observable, so it is not marked CONFIRMED.

---

## B. Why R2 EXECUTION_RESULT was not finalized

### B.1 Root cause

The R2 executor (root Hermes) committed and pushed the implementation commit
`e51f06b3` itself while the host runner was still executing the same task. This
advanced `origin/aither-v2` past the runner's launch HEAD (`d850f55`). When the
host runner reached `stage_commit_push` to publish its own PASS result plus
`.agent/EXECUTION_RESULT.json`, its remote re-fetch returned `e51f06b3` ≠
start_head `d850f55`, so it raised

```
remote moved during execution: expected d850f55a18c0370ea3a0e196c5043b0fc0ba6981, got e51f06b3d38906ac1c3c33a0c2bf1f8516f3b4c1
```

and the run was recorded `BLOCKED` (runner journal, `08:34:54`). The subsequent
`publish_result_commit(BLOCKED)` also failed on the same `remote moved` check and
its result-only commit was abandoned (the two `reset --hard d850f55` entries in
the reflog correspond to the two `restore_after_failed_executor` calls in
`execute_task` and `publish_result_commit`). Consequently `.agent/EXECUTION_RESULT.json`
was never updated to an R2 PASS and still carries the R1 BLOCKED record.

### B.2 Hypothesis test — "remote HEAD moved during executor execution before stage_commit_push"

**CONFIRMED.** This is exactly what the runner's own journal message states and
the reflog corroborates: the remote was `d850f55` when execution began and
`e51f06b3` by the time `stage_commit_push` re-fetched, so the runner aborted
before it could commit/push its PASS result.

### B.3 Confirmed facts vs inference

Confirmed (direct evidence):

- Remote moved from `d850f55` to `e51f06b3` during the R2 execution
  (runner journal `08:34:54`, `remote moved during execution`).
- `e51f06b3` authored/committed through `codex` git identity at `08:32:30`
  (commit metadata + repo git config).
- `e51f06b3` contains 9 implementation paths and no `EXECUTION_RESULT.json`.
- Host runner state records `last_task_id=AITHER-MVP-OPS-RC1-R2`,
  `last_attempt_result=BLOCKED`, `last_commit_sha=63ad4ef...`.
- `runuser(uid=0 -> codex)` git sessions at `08:32:30` (root executor).

Inference (not directly observed):

- That the root Hermes executor (not some external manual actor) is the process
  that executed those git commit/push commands. Supported by timing, the
  `runuser` PAM trail, the `codex` author identity, and the absent `RESULT_PATH`,
  but the executor's command stream is not captured.

---

## C. R2 implementation integrity

- R2 evidence file `docs/operations/OPS_RC1_R2_EVIDENCE.md` exists and matches R2:
  task `AITHER-MVP-OPS-RC1-R2`, baseline `63ad4ef91221aa32cfa3d1be6cdc770787a0a9a4`
  (equal to the R2 `baseline_sha` in the `d850f55` task control).
- No path outside the R2 allowlist was committed in `e51f06b3`
  (all 9 changed paths are in the 14-path R2 allowlist — see A.2).
- This audit performs no destructive or runtime test; repository/governance only.

---

## D. Host-runner finalization test

- Exactly one worktree change is left behind: this file
  `docs/operations/OPS_RC1_R2_GOVERNANCE_AUDIT.md` (the sole `allowed_paths`
  entry for this task).
- No git add/commit/push was performed by this executor.
- Expected success: the host runner detects this one allowed path, writes a PASS
  `.agent/EXECUTION_RESULT.json` for `AITHER-MVP-GOV-R2-FINALIZE-R1`, commits it
  with message `governance: finalize OPS-RC1-R2 handoff`, pushes, and leaves a
  clean worktree.

---

## Required audit conclusion

```
R2_IMPLEMENTATION_COMMIT: e51f06b3d38906ac1c3c33a0c2bf1f8516f3b4c1
R2_SCOPE_INTEGRITY: PASS
R2_EXECUTION_RESULT_PRESENT: NO
ROOT_CAUSE: The R2 executor (root Hermes) self-committed and pushed the R2
  implementation commit e51f06b3 during its own execution, moving
  origin/aither-v2 from d850f55 to e51f06b3 before the host runner could
  publish its own PASS result. The host runner's stage_commit_push then
  detected "remote moved during execution" (expected d850f55, got e51f06b3)
  and aborted with BLOCKED, so .agent/EXECUTION_RESULT.json was never updated
  to an R2 PASS. The executor's self-commit/self-push is a network_git=false /
  governance-separation violation.
ROOT_CAUSE_CONFIDENCE: HIGH
HERMES_GIT_WRITE_USED_IN_THIS_TASK: NO
RUNTIME_MUTATIONS_IN_THIS_TASK: NO
SECRET_VALUES_PRINTED: NO
SECRETS_EXPOSED: NO
```
