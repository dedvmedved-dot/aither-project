# Aither — R7-C1 v2-R1 Alternative Diagnostic Semantics (R1-4)

TASK: `AITHER-HERMES-R8-BENCHMARK-REPAIR-R7C1-V2-R1`

The v2 parser classified historically-observed legitimate read-only diagnostics as
`UNSUPPORTED_SEMANTIC_OPERATION`, repeating a v1 false-negative class. This document
lists each added semantic family and why it is included.

## Added families (R1)

| Family | Semantic operation | Supported command family | Scenario classes | Safety |
|---|---|---|---|---|
| Port/listener diagnostics | `SocketListeners(port=None\|int)` | `ss -ltnp`, `ss -tlnp`, `ss ... \| grep ':80'`, `netstat -ltnp`, `netstat -tlnp \| grep ':80'` | linux service bind failures (LIN-01), network | read-only |
| DNS query via shell | `dns_query(hostname)` | `dig <host> [@server]` | network / dns failure (NET, cross) | read-only |

## Rationale

- **SocketListeners**: a real engineer diagnosing an nginx port conflict runs `ss -ltnp`
  or `netstat -ltnp` (not `systemctl`). The benchmark must not penalize this. The family is
  model-independent and read-only.
- **dns_query**: `dig` is the canonical interactive DNS diagnostic and is semantically
  equivalent to the `dns_lookup` tool.

## Already supported (v2, retained)

`df`/`du` disk usage, `crontab -l`, `cat` (read file), `openssl x509` certificate expiry,
`kubectl get endpoints`, `docker exec … nslookup`, `docker images`, `docker build`,
`ceph -s|status|osd tree|osd df|pg stat|pg dump|health detail`, `drbdadm status|role`,
`mount`, `ip link`, `ps aux`, `ls -l`, `id`, `lscpu`, `nvidia-smi`, `psql -c`, `curl -s`.

## Principle

Only general, read-only, model-independent diagnostic families relevant to existing
scenario intents were added. No exact model-output aliases. Unknown-but-safe commands
remain `UNSUPPORTED_SEMANTIC_OPERATION` (distinct from `IRRELEVANT`).
