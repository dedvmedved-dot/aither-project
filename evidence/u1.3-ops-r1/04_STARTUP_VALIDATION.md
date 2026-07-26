# U1.3-OPS-R1 — ВАЛИДАЦИЯ ЗАПУСКА (STARTUP)

**Метка времени:** 2026-07-26T01:26:21Z  
**Источник:** logs/04-startup.log

## Проверка статуса развёртывания

Выполнена команда `kubectl rollout status` для всех 10 deployments кластера. Все развёртывания успешно завершены.

| # | Deployment | Статус |
|---|------------|:------:|
| 1 | aither-ai-platform | ✅ успешно |
| 2 | aither-bff | ✅ успешно |
| 3 | aither-identity | ✅ успешно |
| 4 | aither-portal | ✅ успешно |
| 5 | aither-portal-backend | ✅ успешно |
| 6 | aither-portal-frontend | ✅ успешно |
| 7 | aither-redis-rate-limit | ✅ успешно |
| 8 | nginx-gateway-32b | ✅ успешно |
| 9 | vllm-14b-instruct | ✅ успешно |
| 10 | vllm-32b-gptq | ✅ успешно |

## Итоговый статус подов

Все 10 рабочих подов в статусе `Running`, все контейнеры `READY 1/1` (кроме nginx-gateway-32b — 2/2, два экземпляра).

| Pod | Готовность | Статус | Рестарты |
|-----|:----------:|--------|:--------:|
| aither-ai-platform-84c478c874-75plb | 1/1 | Running | 0 |
| aither-bff-85f756f59-gd5gv | 1/1 | Running | 0 |
| aither-identity-67b5994997-2jdvd | 1/1 | Running | 0 |
| aither-portal-6c445cc9f-44dzd | 1/1 | Running | 0 |
| aither-portal-backend-559754567d-599kk | 1/1 | Running | 0 |
| aither-portal-frontend-5cc6d99997-btksr | 1/1 | Running | 0 |
| aither-redis-rate-limit-754cdd9784-stnl6 | 1/1 | Running | 0 |
| nginx-gateway-32b-65786797-k8skw | 1/1 | Running | 0 |
| nginx-gateway-32b-65786797-px4rz | 1/1 | Running | 0 |
| vllm-14b-instruct-7f6f784dcb-g2h5d | 1/1 | Running | 0 |
| vllm-32b-gptq-7d6dc7c64-r82nh | 1/1 | Running | 0 |

## Итоговый статус deployments

Все 10 deployments: READY = UP-TO-DATE = AVAILABLE.

| Deployment | READY | UP-TO-DATE | AVAILABLE |
|------------|:-----:|:----------:|:---------:|
| aither-ai-platform | 1/1 | 1 | 1 |
| aither-bff | 1/1 | 1 | 1 |
| aither-identity | 1/1 | 1 | 1 |
| aither-portal | 1/1 | 1 | 1 |
| aither-portal-backend | 1/1 | 1 | 1 |
| aither-portal-frontend | 1/1 | 1 | 1 |
| aither-redis-rate-limit | 1/1 | 1 | 1 |
| nginx-gateway-32b | 2/2 | 2 | 2 |
| vllm-14b-instruct | 1/1 | 1 | 1 |
| vllm-32b-gptq | 1/1 | 1 | 1 |

## Заключение

**Все 10 deployments успешно запущены и находятся в состоянии Ready. Ошибок при запуске не обнаружено.** EXIT_CODE=0 для всех проверок.
