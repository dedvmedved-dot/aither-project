
# 07-REPOSITORY-CHECKLIST

**Project:** Aither / AI Hermes MVP

## Purpose

Defines the mandatory repository verification checklist before RC1 acceptance.

## Repository Structure

Verify:

- docs/stage10/
- reports/
- evidence/
- required project directories
- absence of unexpected files

## Commit Verification

Confirm:

- repository
- branch
- Commit SHA
- Parent SHA
- commit message
- author
- timestamp

## File Verification

Confirm:

- expected files only;
- no unauthorized deletions;
- no unexpected runtime modifications;
- UTF-8 encoding;
- valid Markdown.

## Documentation

Verify:

- numbering;
- headings;
- code blocks;
- links;
- terminology consistency.

## Evidence

Confirm:

- traceability;
- reproducibility;
- referenced Commit SHA;
- accessible artifacts.

## Git Checks

Recommended:

```bash
git status
git diff --check
git show --stat HEAD
git diff HEAD^..HEAD --name-only
```

## Acceptance Checklist

- Repository consistent
- Scope respected
- Evidence complete
- Findings reviewed
- External audit completed
- CONNECTOR VERIFIED obtained
- PASSED decision issued

## Final Rule

Repository readiness is confirmed only after independent external audit.
