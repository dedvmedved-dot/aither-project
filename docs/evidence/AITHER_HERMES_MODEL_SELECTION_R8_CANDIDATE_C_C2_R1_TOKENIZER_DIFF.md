# Aither — R8 Candidate C-C2-R1 Tokenizer Diff

TASK: AITHER-HERMES-AGENT-MODEL-SELECTION-R8-CANDIDATE-C-C2-R1-TOKENIZER-COMPATIBILITY-CLOSURE-AND-RUNTIME-RESUME

## Diff (base e1df551 vs AWQ 5d029d18)

`tokenization_kimi.py` — exactly ONE line differs (line 19):

```
base (e1df551): from transformers.convert_slow_tokenizer import bytes_to_unicode
awq  (5d029d18): from transformers.models.gpt2.tokenization_gpt2 import bytes_to_unicode
```

- Classification: COMPATIBILITY_ONLY (import source only; `bytes_to_unicode()` usage is identical).
- No tokenization-semantics change.

SHA256:
- base tokenization_kimi.py: b6b304f63d355f29f5f5aa27694337c824c90e1ac80559ca537909824729761f
- awq  tokenization_kimi.py: 1193638fef9e47e6360b97745691c6c8ff06879c20809feefd9a6ac65e985511
- patched (awq, after fix): b6b304f63d355f29f5f5aa27694337c824c90e1ac80559ca537909824729761f (== base)

## Tokenizer asset comparison

- tiktoken.model: MATCH (LFS oid b6c497a7469b33ce, size 2795286, both)
- tokenizer_config.json: IDENTICAL (3695 bytes)
- chat_template.jinja: IDENTICAL (1850 bytes)
- configuration_kimi.py: same size (4948)
- special_tokens_map.json: DIFFERS — base has additional_special_tokens `[extra_id_0..255]` + headers;
  AWQ trims to `<|im_*|>` + headers. Immaterial for text/tool tokenization (core BPE vocab + added tokens identical).
- modeling_kimi.py: differs (42975 vs 40793) — model code, not tokenizer.
- config.json: differs (AWQ adds quantization_config) — expected.

## Verdict

- TIKTOKEN_MODEL_MATCH=YES
- SPECIAL_TOKENS_MATCH=NO (additional_special_tokens only; immaterial)
- TOKENIZER_CONFIG_COMPATIBLE=YES (identical)
- CHAT_TEMPLATE_COMPATIBLE=YES (identical)
- BASE_AND_AWQ_TOKENIZATION_SEMANTICS_EQUIVALENT=YES (core BPE + added tokens + chat template identical)
- PATCH_SOURCE=MINIMAL_EQUIVALENT_PATCH (base import line)
- PATCH_CHANGES_TOKENIZATION_SEMANTICS=NO
