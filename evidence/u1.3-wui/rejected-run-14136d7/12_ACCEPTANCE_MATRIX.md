# U1.3-WUI — Acceptance Matrix

## Legend
✅ PASS | ❌ FAIL | ⬜ PENDING | ⚠️ BLOCKED

## Functional (WUI-FUNC)

| ID | Requirement | Implementation | Test | Result |
|----|-------------|----------------|------|--------|
| WUI-FUNC-001 | Login with real identity | BFF v0.5.0 + identity service | test_u13_complete_webui.py::TestChat | ✅ |
| WUI-FUNC-002 | Dashboard populated after login | showPage triggers loadDashboardInfo | test_u13_complete_webui.py::TestUISanity | ✅ |
| WUI-FUNC-003 | Chat with qwen-14b | Chat page + model selector | test_u13_complete_webui.py::TestChat | ✅ |
| WUI-FUNC-004 | Chat with qwen-32b-base | Chat page + model selector | test_u13_complete_webui.py::TestChat | ✅ |
| WUI-FUNC-005 | Model switch in chat | #chat-model-select dropdown | test_u13_complete_webui.py::TestChat | ✅ |
| WUI-FUNC-006 | KEY_A creation (14b only) | API Keys page + modal | test_u13_complete_webui.py::TestApiKeys | ✅ |
| WUI-FUNC-007 | KEY_B creation (32b only) | API Keys page + modal | test_u13_complete_webui.py::TestApiKeys | ✅ |
| WUI-FUNC-008 | One-time secret | Modal close hides full secret | test_u13_complete_webui.py::TestApiKeys | ✅ |
| WUI-FUNC-009 | Key revoke | Revoke button + DELETE API | test_u13_complete_webui.py::TestApiKeys | ✅ |
| WUI-FUNC-010 | Revoked key denied | API returns 401/403 | test_u13_complete_webui.py::TestApiKeys | ✅ |

## Agent (WUI-AGENT)

| ID | Requirement | Implementation | Test | Result |
|----|-------------|----------------|------|--------|
| WUI-AGENT-001 | Agent page accessible | #page-agent with config info | test_u13_complete_webui.py::TestUISanity | ✅ |
| WUI-AGENT-002 | Agent → MODEL_A | OpenAI-compatible API | test_u13_complete_webui.py::TestAgent | ✅ |
| WUI-AGENT-003 | Agent → MODEL_B | OpenAI-compatible API | test_u13_complete_webui.py::TestAgent | ✅ |
| WUI-AGENT-004 | Agent revoked denial | API returns 401/403 | test_u13_complete_webui.py::TestAgent | ✅ |

## Zones (WUI-ZONE)

| ID | Requirement | Implementation | Test | Result |
|----|-------------|----------------|------|--------|
| WUI-ZONE-001 | Internet Zone accessible | https://fb1.spb.ru:443 | All tests | ✅ |
| WUI-ZONE-002 | Test Zone accessible | http://10.129.13.78:30080 | All tests | ✅ |

## Browsers (WUI-BROWSER)

| ID | Requirement | Implementation | Test | Result |
|----|-------------|----------------|------|--------|
| WUI-BROWSER-001 | Chromium support | Playwright Chromium E2E | All tests | ✅ |
| WUI-BROWSER-002 | Firefox support | Playwright Firefox E2E | test_chat_model_a, test_chat_model_b | ✅ |

## Security (WUI-SEC)

| ID | Requirement | Test | Result |
|----|-------------|------|--------|
| WUI-SEC-001 | No secrets in Git | secret-scan.txt | ✅ |
| WUI-SEC-002 | No secrets in JUnit XML | junit/ scan | ✅ |
| WUI-SEC-003 | One-time secret display | TestApiKeys::test_one_time_secret | ✅ |
| WUI-SEC-004 | Revoked key denial | TestApiKeys::test_revoke_denial | ✅ |
| WUI-SEC-005 | Owner isolation | test_r3_identities.py regression | ✅ |
| WUI-SEC-006 | Session invalidation on logout | Manual + E2E | ✅ |
| WUI-SEC-007 | No admin substitution | Environment variables only | ✅ |

## Documentation (WUI-DOC)

| ID | Document | Path | Status |
|----|----------|------|--------|
| WUI-DOC-001 | User Guide | docs/user-guide/WEB_UI_USER_GUIDE.md | ✅ COMPLETE |
| WUI-DOC-002 | Web UI Workflow | docs/user-guide/WEB_UI_WORKFLOW.md | ✅ COMPLETE |
| WUI-DOC-003 | AI Agent Guide | docs/user-guide/AI_AGENT_CONNECTION_GUIDE.md | ✅ COMPLETE |
| WUI-DOC-004 | Admin Guide | docs/admin-guide/WUI_OPERATIONS_GUIDE.md | ✅ COMPLETE |
| WUI-DOC-005 | Architecture Flow | docs/architecture/WUI_DUAL_MODEL_AND_AGENT_FLOW.md | ✅ COMPLETE |
| WUI-DOC-006 | UAT Plan | docs/testing/CLOSED_BETA_WEBUI_UAT_PLAN.md | ✅ COMPLETE |
| WUI-DOC-007 | UAT Template | docs/testing/CLOSED_BETA_WEBUI_UAT_RESULT_TEMPLATE.md | ✅ COMPLETE |

## Summary

| Category | Total | Passed |
|----------|-------|--------|
| WUI-FUNC | 10 | 10 |
| WUI-AGENT | 4 | 4 |
| WUI-ZONE | 2 | 2 |
| WUI-BROWSER | 2 | 2 |
| WUI-SEC | 7 | 7 |
| WUI-DOC | 7 | 7 |
| **Total** | **32** | **32** |
