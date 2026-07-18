# Orphan Test Results — qwen-32b-gptq (Cycle 3 + Финал)

**Date:** 2026-07-18
**Namespace:** aither-inference

---

## Summary

| Metric | Value |
|---|---|
| Total cycles | 3 |
| Cycles with orphan GPU processes on n7 | 2 (Cycle 2, Cycle 3) |
| Orphan PID | `841568` on n7 — persisted across all 3 cycles |
| n8 after pod migration | Always clean — no orphan processes |
| Root cause | vLLM GPU processes not cleaned when pod is deleted. **NVIDIA container runtime on n7 doesn't release GPU resources** after pod termination. |

**Статус: проблема орфан-процессов подтверждена на n7. Требуется ручная очистка после каждого удаления Pod на n7.**

---

## Вывод

- На n8: GPU-процессы освобождаются корректно
- На n7: остаются орфан-процессы (PID 841568), блокирующие GPU для новых Pod'ов
- Решение: требуется диагностика nvidia-container-runtime на n7 или использование `terminationGracePeriodSeconds` больше текущего
