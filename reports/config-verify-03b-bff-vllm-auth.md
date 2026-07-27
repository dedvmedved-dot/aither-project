# BFF → vLLM 14B Auth Fix Report

**CHANGE ID:** CHANGE-0021 — Restore BFF → vLLM 14B internal authentication
**Предыдущий checkpoint:** c4f3cab
**Дата:** 27.07.2026 17:30 МСК
**Результат:** ✅ СИСТЕМА РАБОТАЕТ КОРРЕКТНО — ИЗМЕНЕНИЯ НЕ ТРЕБУЮТСЯ

---

## Root Cause Analysis

vLLM 14B возвращал 401 Unauthorized при прямом вызове без ключа — это **корректное поведение**, а не баг. Система настроена на аутентифицированный доступ:

- vLLM 14B: `VLLM_API_KEY` из `Secret/vllm-api-key`
- BFF: `BFF_14B_UPSTREAM_AUTH_TOKEN` из `Secret/aither-bff-auth`

## Secret Fingerprints

| Источник | SHA-256 |
|---|---|
| vLLM Secret (`vllm-api-key`) | `1b9eb68965715225c5c28ed7435343a08b6ac8bda411cfeb2f66cd9f92656fe6` |
| BFF replica 1 (N8) | `1b9eb68965715225c5c28ed7435343a08b6ac8bda411cfeb2f66cd9f92656fe6` |
| BFF replica 2 (N7) | `1b9eb68965715225c5c28ed7435343a08b6ac8bda411cfeb2f66cd9f92656fe6` |

**MATCH ✅ — обе реплики BFF используют тот же ключ, что и vLLM.**

## Configuration Status

| Параметр | До | После | Статус |
|---|---|---|---|
| `BFF_14B_UPSTREAM_AUTH_TOKEN` в BFF env | Присутствует | Присутствует | ✅ Без изменений |
| Secret source | `aither-bff-auth` | `aither-bff-auth` | ✅ Без изменений |
| Код `app.py` | Поддерживает `BFF_14B_UPSTREAM_AUTH_TOKEN` | Без изменений | ✅ |
| vLLM `VLLM_API_KEY` | Установлен | Установлен | ✅ Без изменений |
| BFF реплики | 2/2 Running | 2/2 Running | ✅ Без изменений |
| vLLM 14B | Running | Running | ✅ Без изменений |

## Результаты тестов

| Тест | Результат |
|---|---|
| 6.2 BFF Health | ✅ `{"status":"ok","auth":"configured"}` |
| 6.3 BFF → vLLM authenticated | ✅ STATUS 200, MODELS ['qwen-14b'] |
| 6.4 BFF end-to-end chat (14B) | ✅ `2+2=4` |
| 6.5 Negative test (vLLM без ключа) | ✅ 401 (security preserved) |

## Дельта

| Параметр | Значение |
|---|---|
| Runtime change | NONE |
| Code change | NONE |
| vLLM change | NONE |
| BFF rollout | NOT REQUIRED |
| vLLM restarted | NO |
| Downtime 14B | NONE |
| Secret value exposed | NO |
| Git changes | Report only |
| Canonical manifest update required | NO |

## Recovery Items

Нет — система уже в корректном состоянии.

---

## Вывод

```text
BFF → VLLM 14B AUTH: ALREADY CONFIGURED AND WORKING.
NO FIX REQUIRED.
The 401 on direct vLLM access is BY DESIGN — security feature.
BFF authenticates to vLLM using internal upstream token.
End-to-end chat returns correct responses.
```

**Emergency mode:** ACTIVE
