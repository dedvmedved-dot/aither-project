# Acceptance Rules

1. Codex PASS is not acceptance.
2. Source-changing tasks require independent GitHub Connector audit.
3. Acceptance verifies branch HEAD, full SHA, parent SHA, changed paths, actual diff, and scope compliance.
4. Runtime evidence is CODEX EXECUTION EVIDENCE.
5. Browser/WUI evidence cannot be replaced with curl unless the task explicitly allows it.
6. DB-only facts cannot be Connector-verified.
7. Unauthorized mutation blocks acceptance until classified.
8. Secrets are never printed or committed.
9. Owner-only/manual steps remain manual.
10. Only the ChatGPT Architect may issue PASSED or CONNECTOR VERIFIED.
