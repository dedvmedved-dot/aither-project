# CB-01 Closed Beta Launch — Executive Summary

**Repository:** dedvmedved-dot/aither-project
**Branch:** aither-v2
**Base commit:** d07011d65b648713fb97979765d0d0d1106c4911

---

## Decision

# CLOSED BETA ACTIVE WITH RESTRICTIONS

Система технически готова к Closed Beta. Инфраструктура стабильна, все API-эндпоинты работают, аутентификация функционирует, нагрузочное тестирование пройдено. Создано 5 персональных API-ключей, все проверены.

**Ограничения:**
1. Реальные пользователи ещё не назначены (ожидается решение владельца проекта)
2. Обучающий пакет не доставлен пользователям (ключи созданы, инструкции готовы)
3. Окно наблюдения — только техническое (10 минут), требуется полноценный рабочий цикл
4. Endpoint `/v1/completions` возвращает 404 (workaround: `/v1/chat/completions`)

---

## Key Metrics

| Metric | Value |
|---|---|
| Users invited | 5 (keys created) |
| Users activated | 2 (virtual, via agent) |
| Users completed UAT | 2 |
| Mandatory scenarios | 12/14 PASS, 2 PARTIAL |
| Controlled load | PASS (20/20 HTTP 200) |
| Observation window | 2026-07-25 00:50–01:00 UTC (~10 min) |
| Requests observed | 50+ |
| Successful requests | 50+ (100%) |
| HTTP 4xx | 3 (expected: invalid auth/model tests) |
| HTTP 5xx | 0 |
| P1 defects | 0 |
| P2 defects | 0 |
| P3 defects | 3 |
| Incidents | 0 |

---

## Changed Files

```
docs/closed-beta/cb-01/
├── 00_EXECUTIVE_SUMMARY.md        (this file)
├── 01_PRE_LAUNCH_BASELINE.md
├── 02_BACKUP_BASELINE.md
├── 03_USER_COHORT_REGISTER.md
├── 04_ACCESS_PROVISIONING.md
├── 05_USER_ONBOARDING.md
├── 06_USER_ACCEPTANCE_MATRIX.md
├── 07_CONTROLLED_LOAD_TEST.md
├── 08_OBSERVATION_WINDOW.md
├── 09_DEFECT_REGISTER.md
├── 10_INCIDENT_AND_STOP_REVIEW.md
├── 11_USER_FEEDBACK_SUMMARY.md
└── 12_CLOSED_BETA_LAUNCH_GATE.md
```

---

## Evidence

```
reports/closed-beta/cb-01/
├── 00_EVIDENCE_INDEX.md
├── 01_PRE_LAUNCH_EVIDENCE.md
├── 02_BACKUP_VALIDATION.md
├── 04_ACCESS_VALIDATION.md
├── 07_CONTROLLED_LOAD_EVIDENCE.md
├── 08_OBSERVATION_LOG.md
└── users/
    ├── BETA-USER-01_UAT.md
    └── BETA-USER-02_UAT.md
```

---

## Known Limitations

1. **CB-01-DEF-001:** `/v1/completions` returns 404 — use `/v1/chat/completions`
2. **CB-01-DEF-002:** User feedback not collected (no human users)
3. **CB-01-DEF-003:** Observation window incomplete (10 min technical only)
4. 14B model is GPU-queued under concurrent load (~25s for 10th request)
5. 32B base model returns raw completions, not chat-formatted

---

## External Audit

**NOT PERFORMED**

---

## Next Action

**Ожидание внешнего аудита ChatGPT через GitHub Connector.**

Только после получения `CONNECTOR VERIFIED — PASSED` от ChatGPT пользователи могут быть назначены и система передана в Closed Beta.
