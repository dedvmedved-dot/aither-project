# U1.3-WUI-R1 — MODEL INVENTORY

| Parameter | Value |
|-----------|-------|
| MODEL_A | qwen-14b |
| MODEL_B | qwen-32b-base |
| MODEL_A type | chat (instruct) |
| MODEL_B type | completion (base) |
| MODEL_A context | 128K |
| MODEL_B context | 128K |
| MODEL_A backend | vLLM, GPU 0 |
| MODEL_B backend | vLLM, GPU 0 |
| MODEL_A scope | model:14b:chat |
| MODEL_B scope | model:32b:chat-adapter, model:32b:completion |

**Web UI model IDs:**
- Chat selector: value="qwen-14b", value="qwen-32b-base"
- Key creation modal: value="qwen-14b", value="qwen-32b-base", value="both"

**API model IDs:**
- /v1/models returns: id="qwen-14b", id="qwen-32b-base"
- /v1/chat/completions accepts: model="qwen-14b", model="qwen-32b-base"

**Test model IDs:**
- MODEL_A = "qwen-14b"
- MODEL_B = "qwen-32b-base"

**Consistency: VERIFIED — all layers use same IDs**
