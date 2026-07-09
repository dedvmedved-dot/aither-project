#!/usr/bin/env python3
"""
CPU LoRA fine-tuning для Qwen 2.5 14B (без GPU).
Модель в /models/Qwen2.5-14B-Instruct/
Использует CPU offload — медленно, но для 21 примера норм.
"""

import os, json, math, time
import torch
import torch.nn as nn
from transformers import AutoTokenizer, AutoModelForCausalLM

MODEL_PATH = "/models/Qwen2.5-14B-Instruct"
OUTPUT_DIR = "/models/lora-qwen14b-astra"
DATA_PATH = "/tmp/dataset.jsonl"
LORA_R = 8
LORA_ALPHA = 16
EPOCHS = 3
LR = 2e-4
MAX_LENGTH = 1024

print(f"=== CPU LoRA Training ===")
print(f"Device: CPU (GPU занят vLLM)")

# Датасет
with open(DATA_PATH) as f:
    examples = [json.loads(line) for line in f if line.strip()]
print(f"Примеров: {len(examples)}")

def fmt(ex):
    return f"<|im_start|>system\n{ex['instruction']}<|im_end|>\n<|im_start|>user\n{ex['input']}<|im_end|>\n<|im_start|>assistant\n{ex['output']}<|im_end|>"

texts = [fmt(ex) for ex in examples]

# Токенизатор
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, trust_remote_code=True)
tokenizer.pad_token = tokenizer.eos_token

enc = tokenizer(texts, truncation=True, max_length=MAX_LENGTH, padding=True, return_tensors="pt")
input_ids, attention_mask, labels = enc["input_ids"], enc["attention_mask"], enc["input_ids"].clone()
print(f"Токены: {input_ids.shape}")

# Модель на CPU
print("Загрузка модели на CPU...")
t0 = time.time()
model = AutoModelForCausalLM.from_pretrained(
    MODEL_PATH,
    torch_dtype=torch.float32,
    device_map={"": "cpu"},
    trust_remote_code=True,
    low_cpu_mem_usage=True,
)
print(f"Загружена за {time.time()-t0:.0f}с")

# LoRA
class LoRALinear(nn.Module):
    def __init__(self, linear, r=LORA_R, alpha=LORA_ALPHA):
        super().__init__()
        self.linear = linear
        out_f, in_f = linear.weight.shape
        self.lora_A = nn.Parameter(torch.zeros(r, in_f))
        self.lora_B = nn.Parameter(torch.zeros(out_f, r))
        self.scaling = alpha / r
        nn.init.kaiming_uniform_(self.lora_A, a=math.sqrt(5))
        nn.init.zeros_(self.lora_B)

    def forward(self, x):
        return self.linear(x) + (x @ self.lora_A.T @ self.lora_B.T) * self.scaling

targets = {"q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"}
lora_params = []
replaced = 0

def apply_lora(module):
    global replaced
    for name, child in module.named_children():
        if name in targets and isinstance(child, nn.Linear):
            setattr(module, name, LoRALinear(child))
            lora_params.extend([getattr(module, name).lora_A, getattr(module, name).lora_B])
            replaced += 1
        else:
            apply_lora(child)

apply_lora(model)
print(f"LoRA modules: {replaced}")

for n, p in model.named_parameters():
    p.requires_grad = False
for p in lora_params:
    p.requires_grad = True

trainable = sum(p.numel() for p in lora_params)
print(f"Trainable: {trainable:,}")

# Обучение
optimizer = torch.optim.AdamW(lora_params, lr=LR)
n = len(input_ids)

print(f"\n=== Обучение {EPOCHS} эпох ===")
for epoch in range(EPOCHS):
    total_loss = 0
    t0 = time.time()
    for i in range(n):
        optimizer.zero_grad()
        out = model(input_ids=input_ids[i:i+1], attention_mask=attention_mask[i:i+1], labels=labels[i:i+1])
        out.loss.backward()
        optimizer.step()
        total_loss += out.loss.item()
        if (i+1) % 5 == 0:
            print(f"  [{i+1}/{n}] loss={out.loss.item():.4f}")

    avg_loss = total_loss / n
    print(f"Эпоха {epoch+1}/{EPOCHS}: loss={avg_loss:.4f} ({time.time()-t0:.0f}с)")

# Сохранение
print(f"\nСохранение...")
os.makedirs(OUTPUT_DIR, exist_ok=True)

lora_state = {}
for name, module in model.named_modules():
    if isinstance(module, LoRALinear):
        lora_state[f"{name}.lora_A"] = module.lora_A.data.clone()
        lora_state[f"{name}.lora_B"] = module.lora_B.data.clone()

torch.save(lora_state, os.path.join(OUTPUT_DIR, "adapter_model.pt"))

config = {
    "lora_rank": LORA_R,
    "lora_alpha": LORA_ALPHA,
    "target_modules": sorted(targets),
    "base_model": "Qwen2.5-14B-Instruct",
}
with open(os.path.join(OUTPUT_DIR, "adapter_config.json"), "w") as f:
    json.dump(config, f, indent=2)

tokenizer.save_pretrained(OUTPUT_DIR)
size_mb = sum(os.path.getsize(os.path.join(OUTPUT_DIR, f)) for f in os.listdir(OUTPUT_DIR)) / 1e6
print(f"=== ГОТОВО: {size_mb:.1f} MB ===")
