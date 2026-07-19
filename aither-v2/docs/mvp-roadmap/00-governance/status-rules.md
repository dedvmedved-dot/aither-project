# Status Rules

## Allowed statuses

| Status | Meaning |
|---|---|
| OBSERVED | факт наблюдён, но ещё не доказан как устойчивый |
| HYPOTHESIZED | есть гипотеза, требуется проверка |
| EXECUTED | команда или изменение выполнены |
| DEPLOYED | объект применён в Kubernetes |
| PASSED | проверка прошла по критериям приёмки |
| FAILED | проверка не прошла |
| VERIFIED | результат подтверждён доказательствами |
| MITIGATED | риск временно снижен, но не устранён |
| RESOLVED | проблема устранена и подтверждена |
| RISK ACCEPTED | риск осознанно принят для MVP |
| NOT STARTED | работа ещё не начата |
| PARTIAL | выполнено частично |

## Forbidden status inflation

Запрещено писать:
- final
- complete
- closed
- production-ready
- healthy
- blockers closed

если нет трёх условий:

1. изменение применено;
2. проверка выполнена;
3. доказательство сохранено в `docs/mvp-roadmap/<stage>/`.

## Acceptance formula

DEPLOYED without evidence != PASSED  
PASSED without report != VERIFIED  
VERIFIED requires logs + metrics + artifacts
