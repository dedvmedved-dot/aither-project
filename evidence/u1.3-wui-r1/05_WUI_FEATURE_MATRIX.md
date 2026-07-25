# U1.3-WUI-R1 — WUI FEATURE MATRIX

| ID | Feature | Implementation | Covered By |
|----|---------|----------------|------------|
| WUI-FUNC-001 | Login with real identity | BFF v0.5.0 + identity service | TestChat, TestApiKeys, TestAgent, TestUISanity |
| WUI-FUNC-002 | Dashboard populated after login | showPage → loadDashboardInfo | TestUISanity::test_dashboard_populated |
| WUI-FUNC-003 | Chat with qwen-14b | Chat page + model selector | TestChat::test_chat_model_a (8 parametrized) |
| WUI-FUNC-004 | Chat with qwen-32b-base | Chat page + model selector | TestChat::test_chat_model_b (8 parametrized) |
| WUI-FUNC-005 | Model switch in chat | #chat-model-select dropdown | TestChat::test_model_switch (8 parametrized) |
| WUI-FUNC-006 | KEY_A creation (14b only) | API Keys modal → select qwen-14b | TestApiKeys::test_key_a_creation |
| WUI-FUNC-007 | KEY_B creation (32b only) | API Keys modal → select qwen-32b-base | TestApiKeys::test_key_b_creation |
| WUI-FUNC-008 | One-time secret display | Modal close hides full secret | TestApiKeys::test_one_time_secret |
| WUI-FUNC-009 | Key revoke | Revoke button + DELETE API | TestApiKeys::test_revoke_denial |
| WUI-FUNC-010 | Revoked key denied | API returns 401/403 | TestApiKeys::test_revoke_denial, TestAgent::test_agent_revoked_denial |
