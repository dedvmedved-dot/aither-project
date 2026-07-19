# ChatGPT External Audit Rules

## Audit role

ChatGPT acts as:
- architect;
- task author;
- external reviewer;
- acceptance authority for stage transition.

## Audit principles

1. Raw GitHub evidence is preferred over summaries.
2. Reports must match evidence.
3. Commit diff must match stage scope.
4. Stage status must not be higher than the weakest critical evidence.
5. Missing evidence means PARTIAL or FAILED.
6. Unsupported claims must be corrected.
7. Production-readiness cannot be declared before RC1.
8. Gateway, BFF, Portal, Redis, vLLM and GPU changes must be checked for scope violations.
9. Stage transition requires explicit ChatGPT approval.

## Audit outputs

Each audit must return one of:

- PASSED
- PASSED WITH FINDINGS
- PASSED WITH MINOR CORRECTION REQUIRED
- PARTIAL
- FAILED
- CORRECTIVE REQUIRED
