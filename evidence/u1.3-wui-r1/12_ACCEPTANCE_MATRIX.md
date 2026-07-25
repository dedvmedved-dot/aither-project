# U1.3-WUI-R1 — ACCEPTANCE MATRIX

## Legend
✅ PASS | ❌ FAIL | ⬜ PENDING

## Functional (WUI-FUNC)

| ID | Requirement | Implementation | Test ID | Run | Evidence | Result |
|----|-------------|----------------|---------|-----|----------|--------|
| WUI-FUNC-001 | Login with real identity | BFF v0.5.0 + identity service | test_chat_model_a | R1-final | logs/u13-e2e-final.log | ✅ |
| WUI-FUNC-002 | Dashboard populated | showPage → loadDashboardInfo | test_dashboard_populated | R1-final | logs/u13-e2e-final.log | ✅ |
| WUI-FUNC-003 | Chat with qwen-14b | Chat page + model selector | test_chat_model_a (8×) | R1-final | logs/u13-e2e-final.log | ✅ |
| WUI-FUNC-004 | Chat with qwen-32b-base | Chat page + model selector | test_chat_model_b (8×) | R1-final | logs/u13-e2e-final.log | ✅ |
| WUI-FUNC-005 | Model switch in chat | #chat-model-select | test_model_switch (8×) | R1-final | logs/u13-e2e-final.log | ✅ |
| WUI-FUNC-006 | KEY_A creation (14b) | Modal → select qwen-14b | test_key_a_creation[Internet] | R1-final | logs/u13-e2e-final.log L:46% | ✅ |
| WUI-FUNC-007 | KEY_B creation (32b) | Modal → select qwen-32b-base | test_key_b_creation[Internet] | R1-final | logs/u13-e2e-final.log L:53% | ✅ |
| WUI-FUNC-008 | One-time secret | Modal close hides secret | test_one_time_secret | R1-final | logs/u13-e2e-final.log L:60% | ✅ |
| WUI-FUNC-009 | Key revoke | Revoke button + DELETE API | test_revoke_denial | R1-final | logs/u13-e2e-final.log L:64% | ✅ |
| WUI-FUNC-010 | Revoked key denied | API returns 401/403 | test_revoke_denial + test_agent_revoked_denial | R1-final | logs/u13-e2e-final.log | ✅ |

## Agent (WUI-AGENT)

| ID | Requirement | Implementation | Test ID | Run | Evidence | Result |
|----|-------------|----------------|---------|-----|----------|--------|
| WUI-AGENT-001 | Agent page accessible | #page-agent + renderAgentPage | test_agent_page_accessible[Internet] | R1-final | logs/u13-e2e-final.log L:89% | ✅ |
| WUI-AGENT-002 | Agent → MODEL_A | OpenAI-compatible API | test_agent_model_a[Internet] | R1-final | logs/u13-e2e-final.log L:67% | ✅ |
| WUI-AGENT-003 | Agent → MODEL_B | OpenAI-compatible API | test_agent_model_b[Internet] | R1-final | logs/u13-e2e-final.log L:75% | ✅ |
| WUI-AGENT-004 | Agent revoked denial | API returns 401/403 | test_agent_revoked_denial | R1-final | logs/u13-e2e-final.log L:82% | ✅ |

## Zones (WUI-ZONE)

| ID | Requirement | Test | Result |
|----|-------------|------|--------|
| WUI-ZONE-001 | Internet Zone (https://fb1.spb.ru:443) | All 28 tests (Internet parametrization) | ✅ |
| WUI-ZONE-002 | Test Zone (http://10.129.13.78:30080) | All 28 tests (Test Zone parametrization) | ✅ |

## Browsers (WUI-BROWSER)

| ID | Requirement | Test | Result |
|----|-------------|------|--------|
| WUI-BROWSER-001 | Chromium | All 28 tests (chromium parametrization) | ✅ |
| WUI-BROWSER-002 | Firefox | test_chat_model_a/b + test_model_switch (firefox) | ✅ |

## Security (WUI-SEC)

| ID | Requirement | Evidence | Result |
|----|-------------|----------|--------|
| WUI-SEC-001 | No secrets in Git | Pre-commit hook passed | ✅ |
| WUI-SEC-002 | No secrets in JUnit XML | Manual scan: 0 matches | ✅ |
| WUI-SEC-003 | One-time secret display | test_one_time_secret PASSED | ✅ |
| WUI-SEC-004 | Revoked key denial | test_revoke_denial PASSED | ✅ |
| WUI-SEC-005 | Owner isolation | test_r3_identities.py 10/10 | ✅ |
| WUI-SEC-006 | Model scope enforcement | API key scope model verified | ✅ |
| WUI-SEC-007 | TLS verification (Internet) | Zero TLS warnings in final log | ✅ |
| WUI-SEC-008 | No admin substitution | Login via end-user credentials only | ✅ |

## Documentation (WUI-DOC)

| ID | Document | Path | Status |
|----|----------|------|--------|
| WUI-DOC-001 | User Guide | docs/user-guide/WEB_UI_USER_GUIDE.md | ✅ |
| WUI-DOC-002 | Web UI Workflow | docs/user-guide/WEB_UI_WORKFLOW.md | ✅ |
| WUI-DOC-003 | AI Agent Guide | docs/user-guide/AI_AGENT_CONNECTION_GUIDE.md | ✅ |
| WUI-DOC-004 | Admin Guide | docs/admin-guide/WUI_OPERATIONS_GUIDE.md | ✅ |
| WUI-DOC-005 | Architecture Flow | docs/architecture/WUI_DUAL_MODEL_AND_AGENT_FLOW.md | ✅ |
| WUI-DOC-006 | UAT Plan | docs/testing/CLOSED_BETA_WEBUI_UAT_PLAN.md | ✅ |
| WUI-DOC-007 | UAT Template | docs/testing/CLOSED_BETA_WEBUI_UAT_RESULT_TEMPLATE.md | ✅ |

## Summary

| Category | Total | Passed |
|----------|-------|--------|
| WUI-FUNC | 10 | 10 |
| WUI-AGENT | 4 | 4 |
| WUI-ZONE | 2 | 2 |
| WUI-BROWSER | 2 | 2 |
| WUI-SEC | 8 | 8 |
| WUI-DOC | 7 | 7 |
| **Total** | **33** | **33** |
