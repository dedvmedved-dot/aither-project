# Aither — R8 Candidate C-C2 Representation Provenance

TASK: AITHER-HERMES-AGENT-MODEL-SELECTION-R8-CANDIDATE-C-C2-RUNTIME-FEASIBILITY-AND-PREFLIGHT
CANDIDATE: moonshotai/Kimi-Linear-48B-A3B-Instruct

## Selected representation

- **Repository:** cyankiwi/Kimi-Linear-48B-A3B-Instruct-AWQ-4bit
- **Publisher:** third-party (cyankiwi)
- **Immutable revision SHA:** 5d029d1844aa64ec302e14466be7d0353c6e697f
- **Architecture (declared):** KimiLinearForCausalLM (preserved)
- **model_type:** kimi_linear
- **Base model relation:** base_model:quantized:moonshotai/Kimi-Linear-48B-A3B-Instruct (matches C-C1 revision e1df551a lineage)
- **License:** inherited from base (MIT)

## Quantization (from config.json quantization_config)

- **quant_method:** compressed-tensors
- **format:** pack-quantized
- **weights:** num_bits=4, group_size=32, symmetric=true, strategy=group, type=int, observer=mse
- **input_activations:** null (weight-only)
- **version:** 0.12.3.dev20+gd429903
- **targets:** ["Linear"]
- **ignore:** attention projections (q/k/v/f_a/f_b/b/g_a/g_b/o), MLP/shared-experts, lm_head (kept BF16)
- Effectively: routed experts quantized to int4; attention/MLA/shared-experts/lm_head remain BF16.

## Files / weight bytes

- 7 safetensors shards: model-00001..00007 (5.00+5.00+5.00+5.00+5.00+4.78+0.75 ≈ 30.53 GB)
- Custom code (trust_remote_code): configuration_kimi.py, modeling_kimi.py, tokenization_kimi.py
- Tokenizer: tiktoken.model, tokenizer_config.json, special_tokens_map.json, chat_template.jinja

## vLLM 0.27.1 support

- vllm/models/kimi_k3/nvidia/model.py imports `compressed_tensors` and threads `quant_config` through the
  Kimi Linear layer construction (KimiLinearForCausalLM supports compressed-tensors).
- The int4 pack-quantized (group_size 32, symmetric) is a Marlin-class kernel format; Marlin int4 kernels
  run on Turing/sm75 (established by the Qwen3-32B AWQ production deployment on n8).

REPRESENTATION_PROVENANCE = PASS (static; runtime kernel compatibility to be proven by startup gate)
