# AITHER QWEN3.8-27B CONTEXT CAPACITY AUDIT R1 — Evidence

TASK: AITHER-QWEN38-CONTEXT-CAPACITY-AUDIT-R1
MODE: FORCE_MAJEURE_MANUAL_READ_ONLY_AUDIT
EXECUTOR: HERMES
DATE: 2026-08-25

## 1. Baseline SHA
`68eaa9a9d453e15b0f93197c9db3b04f37cbd232`

## 2. Audit date/time
2026-08-25 (read-only, runtime НЕ менялся)

## 3. Live workload identity
- Deployment: `vllm-qwen38-27b-fp8`
- Pod: `vllm-qwen38-27b-fp8-5b4c7bdf57-qwdcq`
- Node: `bootsmam-k8s-clnt01-n7-gpu` (n7)
- Namespace: `aither-inference`
- Service: `vllm-qwen38-27b-fp8` (ClusterIP :8000)

## 4. Exact image/digest
`vllm/vllm-openai@sha256:0a51ea5b4ae2dc5d81890e5173f54203d2a3ae0cfffe51b8fd2afd4391bfd967`

## 5. Exact vLLM command
`--model /model --served-model-name qwen3.8-27b --tensor-parallel-size 2 --host 0.0.0.0 --port 8000 --gpu-memory-utilization 0.90 --max-model-len 16384 --max-num-seqs 1 --dtype half --enforce-eager --reasoning-parser qwen3`

## 6. Current max-model-len
`16384`

## 7. TP
`2`

## 8. GPU inventory
- GPU0: Quadro RTX 6000, 23040 MiB total, 19307 MiB used, 3195 MiB free
- GPU1: Quadro RTX 6000, 23040 MiB total, 19307 MiB used, 3195 MiB free
- (2× NVIDIA RTX 6000 Turing, 24 GB)

## 9. GPU idle snapshots (3 сэмпла, стабильно)
mean used = 19307 MiB, mean free = 3195 MiB per GPU

## 10. Model config architecture
- model_type = `qwen3_5_text`
- num_hidden_layers = 64
- hidden_size = 5120
- num_attention_heads = 24
- num_key_value_heads = 4
- head_dim = 256
- full_attention_interval = 4
- max_position_embeddings = 262144
- quantization: fp8 (e4m3, weight-only)

## 11. Native context
`NATIVE_CONTEXT_SUPPORTED = YES`, `NATIVE_CONTEXT_VALUE = 262144`

## 12. KV dtype
`KV_CACHE_DTYPE = auto` → резолвится в **FP16** (compute dtype `torch.float16`; явный `--kv-cache-dtype` не задан). FP8 — только weight-only (Marlin kernel, нет нативного FP8 на Turing).

## 13. Full-attention layer count
`FULL_ATTN_LAYERS = 16` (full_attention_interval=4, 64/4)

## 14. Hybrid layer count
`HYBRID_LAYERS = 48` (linear attention / DeltaNet)

## 15. KV formula
```
KV_bytes_per_token_per_GPU =
  16 (full-attn layers) × 2 (kv_heads_per_GPU) × 256 (head_dim) × 2 (K+V) × 2 (FP16 bytes)
  = 32,768 bytes = 32 KiB/token/GPU
```

## 16. Bytes/token/GPU
`32768` bytes/token/GPU (≈ 32 KiB)

## 17. Theoretical table (full-attention KV, per GPU)
| Context | KV/GPU |
|---|---|
| 16K | 0.5 GiB |
| 32K | 1.0 GiB |
| 48K | 1.5 GiB |
| 64K | 2.0 GiB |
| 96K | 3.0 GiB |
| 128K | 4.0 GiB |
| 192K | 6.0 GiB |
| 256K | 8.0 GiB |

## 18. vLLM reported KV capacity
`VLLM_GPU_KV_CACHE_TOKENS = 75,776` (Available KV cache memory: 2.67 GiB/GPU)

## 19. Maximum concurrency
`VLLM_MAX_CONCURRENCY_CURRENT = 4.62x` (для 16,384 tokens)

## 20. 12K–14K probe
- INPUT_TOKENS = 8393 (synthetic, ~46K chars)
- MAX_OUTPUT_TOKENS = 128, фактически 10
- WALL_SEC = 19.3 (prefill ~19s + 10 output tokens)
- prefill throughput ≈ 442 tokens/s

## 21. GPU probe snapshots
GPU0/GPU1 used остались 19307 MiB (KV пред-аллоцирован, префилл не увеличил memory)

## 22. Latency
- Generation: **~9 tokens/s** (221 tokens/24s; vLLM metrics 9.2–9.3 tok/s)
- Prefill: ~442 tokens/s
- OWNER baseline: 2048-token block ≈ 240s (согласуется с ~9 tok/s)

## 23. Timeout chain (read-only)
- backend→vLLM: 300s (main.py)
- Portal nginx `/api/`: 330s
- VPS2 nginx `/api/` и `/v1/chat/completions`: 330s

## 24. Memory verdict
`GPU_MEMORY_FIT_64K = YES` — KV cache 75,776 tokens > 65,536; 64K KV ≈ 2 GiB/GPU (в пределах текущих 2.67 GiB). Headroom ~2.2 GiB/GPU.

## 25. Latency/UX verdict
`UX_RISK_64K = HIGH` — generation ~9 tok/s (2048 tokens ≈ 228s); 64K prefill ≈ ~145s (линейная экстраполяция 8.4K→19s). 64K + длинный вывод (>2048 токенов) превышает 300s backend timeout.

## 26. Overall verdict
`CONDITIONAL_GO_64K` — память позволяет, но требуется controlled staged change + валидация + timeout/UX условия.

## 27. Exact conditions
1. Staged 32K → 64K (не прыжком).
2. Только `--max-model-len` (не трогать gpu-memory-utilization, max-num-seqs, kv-cache-dtype).
3. Startup-валидация: `GPU KV cache size >= 65536`.
4. Timeout path: для 64K + длинный вывод потребуется > 300s (решить отдельно).
5. Rollback gates (см. п.29).

## 28. Future controlled-change design (DESIGN ONLY, не выполнять)
- Phase 1: max-model-len=32768 → startup + health + cache logs + memory + probe.
- Phase 2: max-model-len=65536 → startup + short prompt + 32K + 48K + ~60K + rollback gates.

## 29. Rollback criteria
pod crashloop / CUDA OOM / vLLM startup failure / `GPU KV cache size < 65536` / health≠200 / model missing / 5xx-504 на длинном запросе / VRAM free ниже запаса / неприемлемая latency.

## 30. HOLD preserved
`.agent/CURRENT_TASK.json` = `AITHER-ARCHITECT-HOLD-ALL-AUTOMATION-R1` (не менялся).

## 31. Backlog preserved
Да — не тронуты streaming, auto-continue, server-side history, billing, tariffs, OAuth, RAG, observability, governance runner repair.

## 32. AI_CODEX_USED: NO
## 33. AUTOMATED_RUNNER_USED: NO
## 34. SECRETS_EXPOSED: NO
