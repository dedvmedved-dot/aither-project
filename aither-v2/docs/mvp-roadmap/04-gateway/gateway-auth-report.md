# Gateway Auth Report

Date: 2026-07-19
Executor: hermes@vps2
Repository branch: aither-v2
Commit: (this commit)

## 1. Objective

Проверить gateway auth и endpoint policy после hardening.

## 2. Evidence

| Check | Evidence |
|---|---|
| no token | evidence/no-token-401.txt |
| wrong token | evidence/wrong-token-401.txt |
| valid token | evidence/valid-token-200.txt |
| chat blocked | evidence/chat-blocked-422.txt |
| completion | evidence/completion-200.txt |

## 3. Results

| Check | Expected | Actual | Status |
|---|---|---|---|
| no token | 401/403 | 401 | PASSED |
| wrong token | 401/403 | 401 | PASSED |
| valid token completion | 200 | 200 | PASSED |
| chat endpoint | 422 | 422 | PASSED |
| completion endpoint | 200 | 200 | PASSED |

## 4. Conclusion

Status: PASSED
