# BFF Routing Policy

## MVP Policy

1. Пользовательские клиенты должны обращаться только к BFF.
2. Portal должен обращаться только к BFF.
3. BFF является единственным пользовательским backend для inference.
4. BFF маршрутизирует 14B traffic в approved 14B backend (vllm-14b-instruct).
5. BFF маршрутизирует 32B completion traffic через nginx-gateway-32b.
6. BFF не должен маршрутизировать 32B chat напрямую в vllm-32b-gptq (gateway blocks with 422).
7. Direct vLLM Services являются internal-only.
8. Direct gateway access является internal-only для BFF-to-gateway traffic.
9. Stage 07 Portal должен проверить схему Portal -> BFF only.
10. Stage 08 Security/NetworkPolicy должен решить, нужно ли ограничивать direct vLLM/gateway access на сетевом уровне.

## Implementation

BFF is implemented as nginx reverse proxy:
- `/api/v1/chat` → `vllm-14b-instruct:8000/v1/chat/completions`
- `/api/v1/completions` → `nginx-gateway-32b:8000/v1/completions`

32B chat requests that reach the gateway are blocked with HTTP 422.
