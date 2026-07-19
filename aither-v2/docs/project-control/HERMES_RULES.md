# Hermes + DeepSeek Execution Rules

## Mandatory rules

1. Evidence first, conclusion second.
2. Do not overstate status.
3. Do not write PASSED when evidence is missing.
4. Do not hide FAILED, PARTIAL, Timeout, OOM, ImagePullBackOff, CrashLoopBackOff, or rollout failure.
5. Do not modify production manifests outside the stage scope.
6. Do not change vLLM/GPU/TP/BFF/Portal/Redis/OAuth unless explicitly approved.
7. Do not transition to next stage without ChatGPT external audit.
8. Always return commit hash and raw GitHub evidence links.
9. Always check `git show --name-only` and `git diff --stat`.
10. Every stage must contain reports, evidence, logs, and updated status.
11. If something cannot be collected, create a file with:
    - Status: NOT COLLECTED
    - Reason:
    - Impact:
12. If a test is not applicable, create a file with:
    - Status: NOT APPLICABLE
    - Reason:
    - Impact:

## Allowed statuses

- OBSERVED
- HYPOTHESIZED
- EXECUTED
- DEPLOYED
- PASSED
- FAILED
- VERIFIED
- MITIGATED
- RESOLVED
- RISK ACCEPTED
- NOT STARTED
- PARTIAL
- POSTPONED
- CORRECTIVE REQUIRED
