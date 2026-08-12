# Governance

## Permanent Operating Model

Architect defines task
-> Codex verifies baseline
-> Codex implements authorized scope
-> local validator
-> tests/evidence
-> one commit
-> push
-> GitHub/CI
-> Architect independent Connector audit
-> PASSED or correction task

## Evidence Classes

- HERMES EXECUTION EVIDENCE
- CODEX EXECUTION EVIDENCE
- OWNER MANUAL EVIDENCE
- CONNECTOR VERIFIED

Runtime facts reported by Codex are not Connector verification.

## Emergency Mode

Emergency mode remains active until the Owner says exactly:

`ФОРС-МАЖОРНЫЙ РЕЖИМ ЗАВЕРШЁН`

Emergency focus:

- Permanent external agent/API path.
- Blocking security defects.
- No unrelated backlog work.

External API target:

`https://fb1.spb.ru:10443/v1/*`

Normal external user path:

registered account -> `aither_...` API key -> Bearer authentication

Normal external users must not require admin credentials, browser JWT, SSH, kubectl,
port-forward, cron, Redis token, gateway admin key, or password as agent credential.

## Scope Contract

- `qwen2.5-32b-instruct` -> `model:qwen2.5:chat`
- `qwen3-32b` -> `model:qwen3:chat`

Legacy transition scope:

- `model:32b:chat`
- Temporary compatibility only; never reintroduce as a new issuer default.

`UPSTREAM_14B_*` is a stale variable name only; do not change routing merely because
of the name.
