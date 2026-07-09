#!/usr/bin/env python3
"""
Конвертер LoRA весов из кастомного формата в формат vLLM (safetensors).
Читает adapter_model.pt, конвертирует в safetensors для vLLM.
"""

import sys, os, json
import torch
from safetensors.torch import save_file

INPUT_DIR = sys.argv[1] if len(sys.argv) > 1 else "/models/lora-qwen14b-astra"

print(f"Конвертация {INPUT_DIR}...")

# Загружаем кастомный формат
state = torch.load(os.path.join(INPUT_DIR, "adapter_model.pt"), map_location="cpu", weights_only=True)

# Конвертируем в safetensors
safetensors_state = {}
for key, tensor in state.items():
    if isinstance(tensor, float):
        # scaling factor — сохраняем в конфиг
        continue
    # Конвертируем в float16 для экономии
    safetensors_state[key] = tensor.to(torch.float16)

output_path = os.path.join(INPUT_DIR, "adapter_model.safetensors")
save_file(safetensors_state, output_path)

# Обновляем конфиг
config_path = os.path.join(INPUT_DIR, "adapter_config.json")
if os.path.exists(config_path):
    with open(config_path) as f:
        config = json.load(f)
    config["peft_type"] = "LORA"
    config["task_type"] = "CAUSAL_LM"
    config["base_model_name_or_path"] = config.get("base_model", "Qwen2.5-14B-Instruct")
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

size_mb = os.path.getsize(output_path) / 1e6
print(f"Конвертировано: {output_path} ({size_mb:.1f} MB)")
print("ГОТОВО")
