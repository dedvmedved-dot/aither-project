# CODEX-HARNESS-S2-HOST-BOOTSTRAP-R3

Architect-owned correction; do not execute with Codex.

Root cause confirmed by diagnostic tag: `fail-codex-path`.

Correction:
- first try `command -v codex` without depending on a login-shell profile;
- if absent from PATH, discover executable Codex under `/home/codex/.nvm/versions/node/*/bin/codex`;
- preserve the existing safe diagnostic status-tag channel.

The next Architect commit republishes the autonomous canary.
