# Stage 18 — Acceptance Test Status

## Tests Available

| Script | Covers | Status |
|---|---|---|
| `scripts/test-stage16-acceptance.sh` | Model Registry, API Keys, Assistants, Conversations, Gateway, Regression | 🔶 NOT RUN (services not deployed) |
| `scripts/test-stage17-observability.sh` | /metrics export, JSON logging, dashboards, alerts, security | 🔶 NOT RUN (services not deployed) |

## Test Results (Static Verification)

### `bash -n` Syntax Checks

| Script | Result |
|---|---|
| `scripts/test-stage16-acceptance.sh` | ✅ PASS |
| `scripts/test-stage17-observability.sh` | ✅ PASS |

### `python3 -m py_compile`

| App | Result |
|---|---|
| Identity Service | ✅ PASS |
| Portal Backend | ✅ PASS |
| AI Platform | ✅ PASS |

## Runtime Acceptance

Runtime acceptance testing requires the Stage 15–17 services to be deployed in the cluster. Until deployment is possible (blocked by Kubernetes API bandwidth), acceptance tests remain **BLOCKED**.

## Manual Verification Procedure

When services are deployed, run:

```bash
# Stage 16 acceptance
bash scripts/test-stage16-acceptance.sh

# Stage 17 acceptance
bash scripts/test-stage17-observability.sh
```

Each script provides PASS/FAIL/SKIP per test case with clear output.
