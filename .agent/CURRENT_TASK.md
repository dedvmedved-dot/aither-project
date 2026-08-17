# TASK: AITHER-MVP-ROADMAP-RECONCILIATION-R1

## Goal

Reconcile `ROADMAP-RECOVERY.md` with the actual Aither project state after the late security, runtime-recovery and H0-H8 autonomy work. This is the first normal bounded work package after the autonomous handoff gates.

Update **only** `ROADMAP-RECOVERY.md`. Do not change application source, manifests, runtime, Kubernetes, databases, deployments, packages, secrets or host configuration.

## Starting state

- Branch: `aither-v2`
- Baseline: `8e97e1ed576ffbf7a8a3eeb067e0f1b8c6e83a98`
- H8 autonomous handoff gate: PASS / Architect accepted.
- Current model scope contract in `.agent/GOVERNANCE.md`:
  - `qwen2.5-32b-instruct` -> `model:qwen2.5:chat`
  - `qwen3-32b` -> `model:qwen3:chat`
  - `model:32b:chat` is legacy compatibility only.
  - `UPSTREAM_14B_*` is a stale variable name only.
- The old recovery roadmap still uses retired generic model labels `14B` and `32B` and an obsolete 27.07.2026 / 68% snapshot.
- The repository also contains old manifests and historical evidence with obsolete model names. They are evidence of drift; they do not override the current scope contract for this roadmap reconciliation.

## Required reconciliation

1. Read the current roadmap plus repository history/evidence relevant to its open items. Use only evidence actually present. Do not invent runtime facts.
2. Remove **all uppercase legacy roadmap labels** `14B` and `32B` from `ROADMAP-RECOVERY.md`. Replace model references with the current exact IDs `qwen2.5-32b-instruct` and `qwen3-32b`, or use model-neutral wording where the evidence does not support a specific model.
3. Preserve useful legacy task numbering, but reclassify each formerly open item conservatively using these explicit states where appropriate:
   - `DONE`
   - `PARTIAL`
   - `OPEN`
   - `OWNER_REQUIRED`
   - `HARDWARE_DEFERRED`
   - `SUPERSEDED`
4. Do not mark a runtime task DONE merely because source/config exists. Runtime completion requires existing accepted runtime evidence.
5. Reconcile the emergency-stabilization items against later accepted runtime recovery. Do not reopen the closed Qwen3 GPU admission incident unless an unresolved requirement remains distinct from that incident.
6. Reconcile security items against the later REG/C2 work present in Git history/evidence. Distinguish completed code/security work from Owner-only browser/email/credential evidence.
7. Add a dated reconciliation header for 2026-08-17 and baseline SHA.
8. Add a section `Current model contract` containing the two current exact model IDs above and explaining that old generic model-size labels have been retired from the roadmap.
9. Add a supplemental completed track for H0-H8 autonomous execution, without renumbering the original 59 legacy tasks.
10. Replace the obsolete 40/59 = 68% summary with a new conservative summary derived from the reconciled statuses. Keep the old 68% only as an explicitly labelled historical snapshot if it is useful; otherwise remove it.
11. Separate active RC1 blockers from `HARDWARE_DEFERRED` items. Do not silently declare hardware-deferred work outside RC1: mark that release-scope decision as requiring Architect/Owner approval if not already evidenced.
12. End the roadmap with a short proposed critical path to RC1, expressed as larger bounded gates rather than one-command STOP tasks. This proposal is **for Owner approval only** and must not launch any next task.
13. Note repository drift discovered during reconciliation: legacy manifests/catalogs may still contain retired model naming and require a later dedicated configuration-alignment task; do not modify those files in this task.

## Required evidence discipline

- GitHub/source facts may be stated as repository evidence.
- Accepted runtime evidence may be used when present in the repository/task history.
- Unknown live runtime state remains `PARTIAL` or `OPEN`, not guessed.
- Owner-only actions remain `OWNER_REQUIRED`.
- Do not print or copy secret values.

## Validation / PASS criteria

PASS only if:

- only `ROADMAP-RECOVERY.md` is modified by the executor;
- the roadmap contains no uppercase `14B` or `32B` legacy labels;
- it contains both `qwen2.5-32b-instruct` and `qwen3-32b`;
- it contains an updated reconciliation date/baseline;
- every unresolved legacy item is conservatively classified;
- H0-H8 is represented as completed supplemental work;
- the obsolete 68% snapshot is no longer presented as current truth;
- the roadmap ends with a proposed RC1 critical path awaiting Owner approval;
- no runtime or application changes are made.

Return PASS and STOP. Do not declare Architect acceptance.
