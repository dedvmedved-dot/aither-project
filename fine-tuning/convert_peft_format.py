#!/usr/bin/env python3
"""
Конвертер кастомных LoRA весов → PEFT-совместимый safetensors для vLLM.
Мой формат:  model.layers.N.module.lora_A, model.layers.N.module.lora_B
PEFT формат: base_model.model.model.layers.N.self_attn.module.lora_A.weight
                                           или .mlp.module.lora_A.weight
"""

import os, sys, json, re
import torch
from safetensors.torch import save_file

INPUT_DIR = sys.argv[1] if len(sys.argv) > 1 else "/models/lora-qwen14b-astra"

print(f"Конвертация {INPUT_DIR} → PEFT-формат...")

# Загружаем кастомные веса
state = torch.load(os.path.join(INPUT_DIR, "adapter_model.pt"), map_location="cpu", weights_only=True)

# Mapping: кастомный формат → PEFT формат
# Кастомный:  model.layers.0.self_attn.q_proj.lora_A
# PEFT:       base_model.model.model.layers.0.self_attn.q_proj.lora_A.weight

peft_state = {}
for key, tensor in state.items():
    if isinstance(tensor, float):
        continue  # scaling factor — не веса

    # Пропускаем тензоры, которые не являются параметрами (scaling и т.д.)
    if tensor.dim() == 0:
        continue

    # Преобразуем имя ключа
    # model.layers.N.self_attn.q_proj.lora_A → base_model.model.model.layers.N.self_attn.q_proj.lora_A.weight
    # model.layers.N.mlp.gate_proj.lora_A    → base_model.model.model.layers.N.mlp.gate_proj.lora_A.weight

    if key.startswith("model."):
        new_key = "base_model.model." + key + ".weight"
    else:
        new_key = "base_model.model.model." + key + ".weight"

    peft_state[new_key] = tensor.to(torch.float16)

# Сохраняем safetensors
output_path = os.path.join(INPUT_DIR, "adapter_model.safetensors")
save_file(peft_state, output_path)

# Обновляем конфиг для vLLM
config_path = os.path.join(INPUT_DIR, "adapter_config.json")
with open(config_path) as f:
    cfg = json.load(f)

# Стандартные поля PEFT, которые ожидает vLLM
cfg["r"] = cfg.get("lora_rank", 8)
cfg["lora_alpha"] = cfg.get("lora_alpha", 16)
cfg["peft_type"] = "LORA"
cfg["task_type"] = "CAUSAL_LM"
cfg["base_model_name_or_path"] = "/models/Qwen2.5-14B-Instruct"
cfg["target_modules"] = cfg.get("target_modules", [
    "q_proj", "k_proj", "v_proj", "o_proj",
    "gate_proj", "up_proj", "down_proj",
])
cfg["bias"] = "none"
cfg["fan_in_fan_out"] = False
cfg["inference_mode"] = True

with open(config_path, "w") as f:
    json.dump(cfg, f, indent=2, ensure_ascii=False)

# Статистика
size_mb = os.path.getsize(output_path) / 1e6
print(f"Ключей: {len(peft_state)}")
print(f"Размер safetensors: {size_mb:.1f} MB")
print(f"Пример ключа: {list(peft_state.keys())[0]}")
print(f"ГОТОВО: {output_path}")
