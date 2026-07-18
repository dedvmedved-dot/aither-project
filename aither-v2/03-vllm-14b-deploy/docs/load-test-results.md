# Load Test Results

**Date:** 2026-07-18

---

## 1. Service DNS — 14B

**DNS:** `vllm-14b-instruct.aither-inference.svc.cluster.local` → `10.108.67.57` ✅  
**curl /v1/chat/completions:** HTTP 200, `"Hi there! How can I assist you today?"` ✅  
**Timing:** 11.01s response (cold start / first request) ✅

```
Token usage: 31 prompt → 11 completion (42 total)
```

## 2. Service DNS — 32B

**DNS:** `vllm-32b-gptq.aither-inference.svc.cluster.local` → resolves ✅  
**curl:** ❌ **timeout** — Pod in CrashLoopBackOff (bitblas error after --quantization gptq was removed)

## 3. Load test

**Not completed.** Kubernetes API was intermittently unavailable (`i/o timeout`).  
`ab -n 100 -c 2` could not be executed due to API instability.

---

## Вывод

- **14B Service DNS — работает.** Полный путь: DNS → ClusterIP → EndpointSlice → Pod → ответ модели (11s, cold)
- **32B Service DNS — не работает.** Pod не отвечает из-за ошибок загрузки
- **Нагрузочное тестирование — не проведено** из-за нестабильности API сервера
