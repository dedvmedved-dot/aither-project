# Aither — R7-C1 v2-R3 Correction Catalog

TASK: `AITHER-HERMES-R8-BENCHMARK-REPAIR-R7C1-V2-R3`
SOURCE: GitHub Connector audit of v2-R2 (`e1b5082`) — `R7C1_V2_R3_FINAL_CORRECTION_REQUIRED`.

## R3-1 — Fully reproducible converter (FIXED)

The R2 converter imported the R1 harness and relied on an uncommitted `extract_namespace`
definition. The R3 converter is self-contained: it imports only the current R3 harness,
contains all extraction logic inline, is deterministic (byte-identical across runs, verified
by SHA256), and fails closed on ambiguous conversion.

## R3-2 — Namespace extraction / X-04 (FIXED)

`extract_namespace` regex misread "k8s" in "DNS resolution fails in k8s pod" as a namespace.
Replaced with an explicit migration map (K8S-01→prod, X-04→default, all else→default).
No ambiguous regex inference. `X04_EVIDENCE_NAMESPACE = default`, `X04_RELEVANCE_NAMESPACE = default`.

## R3-3 — True source semantic assertions (FIXED)

R2 preservation assigned expected==actual declaratively. R3 independently parses each v1
source key into the expected typed operation (via the R3 semantic parser + namespace map)
and asserts equality against the converted operation. 73/73 evidence items asserted with
real value comparison.

## R3-4 — Remove unjustified ANY (FIXED)

Overly broad wildcards removed: `dns_query(hostname=ANY)`→specific hostname; `disk_usage_*(target=ANY)`
→specific filesystem; `certificate_expiry(path=ANY)`→specific cert path. Remaining `*`/`null`
values are "list-all" queries (e.g. `ss -ltnp` port=None, `ps aux` pattern=*, `nslookup` host=*),
not any-value wildcards. `UNJUSTIFIED_WILDCARDS = 0`.

## R3 cross-tool equivalence (NEW)

`read_file` ≡ `cat`, `http_get` ≡ `curl` unified in the matcher, so equivalent diagnostics via
different tool representations receive the same relevance class.
