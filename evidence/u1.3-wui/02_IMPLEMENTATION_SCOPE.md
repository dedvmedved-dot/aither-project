# U1.3-WUI — Implementation Scope

## Changes from Baseline

### Portal (portal/dist/index.html)

1. **showPage() fix**: Added data loading triggers for dashboard, api-keys, agent, and profile pages
2. **AI Agent Connection page**: New `#page-agent` with API base URL, model IDs, config examples, curl template, error diagnostics table
3. **Navigation**: Added 🤖 AI Agent nav link between API Keys and Documentation
4. **Pages array**: Added 'agent' to supported pages list

### Documentation (docs/)

5. **User Guide**: WEB_UI_USER_GUIDE.md — comprehensive 26-section user guide
6. **Workflow**: WEB_UI_WORKFLOW.md — step-by-step Web UI algorithm
7. **Agent Guide**: AI_AGENT_CONNECTION_GUIDE.md — AI agent connection instructions
8. **Admin Guide**: WUI_OPERATIONS_GUIDE.md — administrator operations guide
9. **Architecture**: WUI_DUAL_MODEL_AND_AGENT_FLOW.md — system architecture flow
10. **UAT Plan**: CLOSED_BETA_WEBUI_UAT_PLAN.md — user acceptance test plan
11. **UAT Template**: CLOSED_BETA_WEBUI_UAT_RESULT_TEMPLATE.md — UAT result form

### Tests (tests/e2e/)

12. **test_u13_complete_webui.py**: New E2E test suite with 4 classes, 14 parametrized tests

### Deployment

13. **aither-portal ConfigMap**: Updated index.html with agent page and fixes
14. **aither-portal-frontend ConfigMap**: Updated with agent page and nginx.conf
15. **Rollout restart**: Both portal and portal-frontend deployments restarted

### NOT Changed

- BFF server.ts (v0.5.0 unchanged)
- API gateway
- Identity service
- Database schema
- Security model
- test_r3_identities.py (Track A accepted tests)
