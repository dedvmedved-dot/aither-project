# U1.3-WUI — Model Inventory

## MODEL_A

- Display name: qwen-14b (Чат)
- Canonical model ID: qwen-14b
- Provider/backend: vLLM (Qwen2.5-14B-Instruct)
- Endpoint route: /models/Qwen2.5-14B-Instruct
- Deployment zone: aither-inference namespace, K8s
- Type: chat (instruction-tuned)
- Health status: ✅ operational

## MODEL_B

- Display name: qwen-32b-base (Базовая)
- Canonical model ID: qwen-32b-base
- Provider/backend: vLLM (Qwen2.5-32B-Instruct-GPTQ)
- Endpoint route: /models/Qwen2.5-32B-Instruct-GPTQ
- Deployment zone: aither-inference namespace, K8s
- Type: completion (base model)
- Health status: ✅ operational

## Verification

Two distinct model IDs confirmed:
- qwen-14b ≠ qwen-32b-base
- Two separate vLLM paths
- Two independent backend deployments with different GPU requirements

## Source

BFF server.ts MODEL_MAP lines 604-613:
- qwen2.5-14b → Qwen2.5-14B-Instruct
- qwen2.5-32b → Qwen2.5-32B-Instruct-GPTQ

Portal model selector uses IDs: qwen-14b, qwen-32b-base
