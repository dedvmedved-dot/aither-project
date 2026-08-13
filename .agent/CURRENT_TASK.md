# TASK: HERMES-INTEGRATION-H0-HOST-DISCOVERY

## Purpose
Determine whether the already-running Telegram-connected Hermes Agent is on the same host as the Aither supervisor and identify only the non-secret execution topology needed for automation.

This is a read-only discovery task. It MUST NOT change Aither, Hermes configuration, systemd, network, Kubernetes, Git configuration, or any runtime resource.

## Required evidence
Create exactly `evidence/hermes-integration/h0-host-discovery.md` with these headings:

- `# Hermes Integration H0 Host Discovery`
- `## Supervisor Host`
- `## Hermes Process Discovery`
- `## Local Hermes Binary`
- `## Gateway/API Observation`
- `## Conclusion`
- `## Result`

Record only:
1. supervisor hostname and current Linux username;
2. whether a `hermes` executable is visible in the current user's PATH, and its executable path if visible;
3. whether one or more running processes appear to be Hermes/Hermes Gateway; for each, record only process owner and a sanitized role such as `gateway`, `hermes`, or `unknown` — DO NOT copy full command lines;
4. whether local TCP listeners on loopback ports 8642 (Hermes API Server) and 8644 (Hermes Webhook) are detectable using non-invasive local inspection if permitted by the sandbox; if sandbox/network policy prevents this, explicitly say `NOT OBSERVABLE FROM CODEX SANDBOX` rather than treating it as absence;
5. whether the evidence is sufficient to conclude `SAME_HOST`, `REMOTE_OR_DIFFERENT_USER`, or `INCONCLUSIVE`.

## Allowed commands/examples
Read-only commands such as `hostname`, `id`, `command -v hermes`, `ps`, `pgrep`, and read-only socket/listener inspection are permitted. Use only commands needed for the fields above.

## Hard prohibitions
- DO NOT read `~/.hermes/.env`, `auth.json`, config files, Telegram token files, API keys, SSH keys, environment variables of Hermes processes, `/proc/<pid>/environ`, or any secret store.
- DO NOT print full Hermes process command lines if they may contain arguments; sanitize to owner + role only.
- DO NOT contact Telegram, GitHub, Internet, Aither API, Kubernetes, databases, or remote hosts.
- DO NOT run `kubectl`, `ssh`, `curl` to remote endpoints, package managers, or service control commands.
- DO NOT modify any file except the single evidence file.
- DO NOT declare Aither or D1 PASSED.

## Result semantics
`PASS` means the discovery evidence was collected safely, even if topology conclusion is `INCONCLUSIVE`.
`BLOCKED` only if the required non-secret evidence file cannot be produced safely.

Return PASS/FAIL/BLOCKED and STOP.
