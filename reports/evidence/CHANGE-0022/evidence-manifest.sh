# Evidence Manifest — CHANGE-0022-C2 R7-R5-EMG-GW-R4
# Each test record: { test_id, command, timestamp, target, expected, actual, exit_code, PASS/FAIL, sanitized_output, commit_sha }
COMMIT_SHA=$(cd /root/aither-project-r7-canonical && git rev-parse HEAD 2>/dev/null || echo "unknown")
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

echo "=== EVIDENCE MANIFEST CHANGE-0022-C2 ==="
echo "Commit: $COMMIT_SHA"
echo "Timestamp: $TIMESTAMP"
echo ""

# Directory -> test mapping
# 06-auth/       -> Auth tests (STR-001 base, AUTH-001..)
# 07-rate-limit/ -> Rate limit tests (RATE-001..)
# 08-billing/    -> Billing tests (BILL-001..)
# 09-security/   -> Security ingress/egress tests (SEC-001..)
# 10-vault/      -> Vault tests (VAULT-001..008)
# 11-rag/        -> RAG tests (RAG-001..010)
# 12-admin/      -> Admin drain/undrain tests (ADM-001..)
# 13-metrics-siem/ -> Metrics + SIEM tests (MET-001.., SIEM-001..)
# 16-load/       -> Load tests
# 17-failover/   -> Failover tests
# 20-secret-scan/ -> Secret scan results

# Template for each evidence file:
cat > /root/aither-project-r7-canonical/reports/evidence/CHANGE-0022/evidence-template.md << 'TEMPLATE'
# Evidence Record

| Field | Value |
|-------|-------|
| Test ID | {TEST_ID} |
| Command | {COMMAND} |
| Timestamp | {TIMESTAMP} |
| Target | {TARGET} |
| Expected | {EXPECTED} |
| Actual | {ACTUAL} |
| Exit Code | {EXIT_CODE} |
| Result | {PASS/FAIL} |
| Commit SHA | {COMMIT_SHA} |

## Sanitized Output
```
{SANITIZED_OUTPUT}
```
TEMPLATE

echo "Evidence template created"
echo ""
echo "=== Summary of artifacts ==="
echo "Streaming tests: gateway/tests/integration/test_streaming.py"
echo "SIEM receiver: gateway/siem_receiver.py + deploy/siem/deployment.yaml"
echo "SIEM tests: gateway/tests/integration/test_siem_integration.py"
echo "Vault deployment: deploy/vault/deployment.yaml"
echo "Vault tests: gateway/tests/integration/test_vault.py"
echo "RAG tests: gateway/tests/integration/test_rag.py"
echo "BFF canary: deploy/canary/bff-gateway-canary.yaml"
echo "Evidence dirs: reports/evidence/CHANGE-0022/{06,07,08,09,10,11,12,13,16,17,20}-*/"
