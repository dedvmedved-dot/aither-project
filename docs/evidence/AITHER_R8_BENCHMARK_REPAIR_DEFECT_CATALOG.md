# Aither — R8-BENCHMARK-REPAIR R7-C1 v2: Defect Catalog (Phase 2)

TASK: `AITHER-HERMES-R8-BENCHMARK-REPAIR-R7C1-V2`
SOURCE: R8-CONTROL audit of the R7-C1 measurement stack (baseline `60453bb`).

Each defect below is confirmed by the R8-CONTROL raw ledger (1266 calls, 1164 simulator
`error`, JSON_TOOL_ARGS=100%, HALL=0) and the 100% corrected preflight.

---

## D1 — Exact-string false negative

The v1 simulator matches a tool call to evidence only when the argument string exactly
equals the hidden `evidence.key` string. Legitimate diagnostic variants fail:

- hidden `df -h` vs legitimate `df -h /var` (targeted filesystem);
- hidden `du -sh /var/*` vs legitimate `du -xh --max-depth=1 /var` (same semantic op);
- hidden `ceph -s` vs legitimate `ceph status`.

**Effect:** valid, correct diagnostic calls are classified `not_found`/`empty` →
counted as `irrelevant` → TOOL_PRECISION collapses.

## D2 — Kubernetes context false positive

v1 `arg_key("kubectl_get", args)` reduces resource `"pods"`/`"pod"` to `"pods"` and
ignores namespace entirely. `KubeGet(resource="pods", namespace="prod")` would reveal
the same evidence as `KubeGet(resource="pods", namespace="kube-system")` merely because
`resource=="pods"`. Namespace is a material context dimension and must be part of identity.

## D3 — Object/path identity defects

Distinct objects collapse together:
- different pods (`web` vs `worker` vs `db`) were partially distinguished only by exact
  string; any argument normalization that strips a pod hash suffix could collide;
- different files/directories/objects must not collapse (path identity must be exact
  modulo only the safe path normalization — leading slash).

## D4 — Shell semantic-equivalence defect

Raw command-string equality defines diagnostic equivalence in v1. There is no semantic
parser; `df -h /var` ≠ `df -h`, `ceph -s` ≠ `ceph status`, `du -sh /var/*` ≠
`du -xh --max-depth=1 /var`. A limited deterministic semantic parser is required for the
benchmark-supported read-only operations only.

## D5 — Error classification contamination

A valid supported diagnostic request (e.g. `systemctl status apache` in a service-failure
scenario) returns `not_found`/`empty` from the simulator and is classified `error` →
`irrelevant`. A valid diagnostic that happens not to reveal hidden evidence is NOT
irrelevant; it is a **relevant negative**.

## D6 — Relevance != reveal

v1 computes `relevant = revealed` and `IRRELEVANT_CALL_RATE = (nondup - revealed)/nondup`.
Every simulator miss (D1/D4/D5) is therefore miscounted as `irrelevant`. Relevance and
evidence-reveal must be separate, independently tracked quantities.

## D7 — Preflight exact-tool defect

The R8-CONTROL preflight's error-recovery cases did not enforce the declared expected
initial tool; `ERR_02` (expected `systemctl_status`, actual `shell_readonly`) was scored
by recovery outcome only. Expected-tool enforcement must apply to ordinary, multi-turn,
and error-recovery cases unless the case explicitly declares an allowed semantic class.

## D8 — Negative-control defect

The R8-CONTROL preflight ran negative controls with `tools=None`, so the model had no
opportunity to make an unnecessary tool call — the "no tool" result was forced, not
measured. Negative controls must run with tool definitions available so an unnecessary
call is a real, detectable failure.

---

## Consequence (from R8-CONTROL)

These defects made the R7-C1 benchmark measure the simulator's exact-string matching
success rather than the model's tool competence. The production control model (Qwen3.8),
proven by the corrected preflight to call tools with 100% accuracy, was scored at 2%
task success / 6.6% tool precision / 93% irrelevant / 0/13 long-context — below every
rejected candidate. The benchmark is therefore INVALID FOR MODEL SELECTION.
