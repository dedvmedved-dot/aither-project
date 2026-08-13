# Hermes Integration H0 Host Discovery

## Supervisor Host

- Hostname: `330133.fornex.cloud`
- Current Linux username: `codex`

## Hermes Process Discovery

- A running process appears to be Hermes.
- Process owner: `nobody`
- Sanitized role: `hermes`
- No full process command line or process environment was inspected.

## Local Hermes Binary

- A `hermes` executable is visible in the current user's `PATH`.
- Executable path: `/usr/local/bin/hermes`

## Gateway/API Observation

- Loopback TCP listener on port 8642 (Hermes API Server): `NOT OBSERVABLE FROM CODEX SANDBOX`
- Loopback TCP listener on port 8644 (Hermes Webhook): `NOT OBSERVABLE FROM CODEX SANDBOX`
- Read-only listener inspection was denied because the sandbox could not open the required netlink socket. This is not evidence that either listener is absent.

## Conclusion

`SAME_HOST`

The local Hermes executable and a locally visible running Hermes process are sufficient to conclude that Hermes is present on the supervisor host. The running process uses a different Linux account (`nobody`) from the supervisor account (`codex`). The gateway/API listener state remains unobservable from the Codex sandbox.

## Result

`PASS`

The required non-secret discovery evidence was collected safely. No runtime, configuration, service, network, database, Kubernetes, Git, or secret state was modified.
