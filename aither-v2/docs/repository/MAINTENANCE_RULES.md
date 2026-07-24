# Repository Maintenance Rules

> 10 rules for maintaining the Aither Project repository.

---

## Rule 1: Single Source of Truth

**PROJECT_MASTER.md** is the authoritative governance document. All stage status changes must be reflected here first. CHAT_HANDOVER.md is the append-only audit trail. Never update historical entries in CHAT_HANDOVER.md.

## Rule 2: Freeze Completed Stage Reports

Stage reports (`reports/stage10/`, `reports/ba02r/`, `reports/rc1/`, etc.) are **frozen snapshots** at their creation time. Do NOT modify them after stage completion. If corrections are needed, create a new report in a new subdirectory.

## Rule 3: Isolate Active and Historical Content

All active development must happen inside `aither-v2/`. Root-level directories (`gateway/`, `portal/`, `manifests/`, `docs/`) are historical/archival. Do NOT add new content to root-level directories.

## Rule 4: No Duplicate Content

Avoid creating duplicate copies of files. If a file needs to exist in multiple locations, use symlinks (where appropriate) or reference the canonical location. This rule specifically targets the `aither-send/` anti-pattern.

## Rule 5: Placeholder Hygiene

Empty placeholder directories (`04-*` through `07-*`, `release/mvp-rc1/`) should be either populated with actual content within 2 stages or cleaned up. Do not leave `.gitkeep` files indefinitely.

## Rule 6: Commit Discipline

- Every commit must be in a single logical scope (stage, feature, fix, docs)
- Commit messages follow conventional commits format: `type(scope): description`
- No `--amend`, `--force`, or history-rewriting commands
- Verify `git diff --check` is clean before commit
- Push only after pre-commit verification

## Rule 7: Secret Safety

Never commit real secrets, passwords, tokens, or private keys. Use:
- `REPLACE_ME` placeholders in example files
- `*-secret.example.yaml` with clear warnings
- Environment variables or K8s Secrets for real values
- Regular secret scan: `git ls-files | xargs grep -InE 'password|secret|token|api[_-]?key|private[_-]?key'`

## Rule 8: Evidence Integrity

Evidence files must be:
- Raw command output where possible (not derived summaries)
- Timestamped with ISO 8601
- Linked to specific AC-IDs in acceptance matrices
- Executable: the command that produced the output must be documented
- Verifiable: exit codes, HTTP status codes, pod UIDs must be recorded

## Rule 9: Branch Management

- `aither-v2` is the active development branch
- `main` is historical — do not commit to it
- No tag creation without architect authorization
- Keep `aither-v2` in sync with `origin/aither-v2`
- Branch-specific content should not cross-contaminate

## Rule 10: Documentation Consistency

- Cross-document contradictions must be flagged and resolved before stage acceptance
- All SHA-1 values in governance documents must match actual commit IDs
- Stage U1 roadmap is the authoritative sequence for Track A (User Launch)
- Governance documents (PROJECT_MASTER, CHAT_HANDOVER, current-mvp-status) must share consistent audit status blocks
- When updating status in one governance document, update all three
- Never claim `PASSED`, `CONNECTOR VERIFIED`, or `FINAL ACCEPTANCE COMPLETE` without ChatGPT authorization
