#!/usr/bin/env python3
"""
LoRA fine-tuning на чистом PyTorch (без peft!) для Qwen 2.5 14B.
Модель уже лежит локально в /models/Qwen2.5-14B-Instruct/
"""

import os
import json
import math
import torch
import torch.nn as nn
import torch.nn.functional as F
from transformers import AutoTokenizer, AutoModelForCausalLM

# === Конфигурация ===
MODEL_PATH = "/models/Qwen2.5-14B-Instruct"
OUTPUT_DIR = "/models/lora-qwen14b-astra"
DATA_PATH = "/tmp/dataset.jsonl"
LORA_R = 16
LORA_ALPHA = 32
LORA_DROPOUT = 0.05
BATCH_SIZE = 1
GRAD_ACCUM = 8
EPOCHS = 5
LR = 2e-4
MAX_LENGTH = 2048

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Device: {device}")

# === Загрузка датасета ===
with open(DATA_PATH) as f:
    examples = [json.loads(line) for line in f if line.strip()]
print(f"Примеров: {len(examples)}")

def format_instruction(ex):
    return f"<|im_start|>system\n{ex['instruction']}<|im_end|>\n<|im_start|>user\n{ex['input']}<|im_end|>\n<|im_start|>assistant\n{ex['output']}<|im_end|>"

texts = [format_instruction(ex) for ex in examples]

# === Токенизатор ===
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, trust_remote_code=True)
tokenizer.pad_token = tokenizer.eos_token

# Токенизация
encodings = tokenizer(texts, truncation=True, max_length=MAX_LENGTH, padding=True, return_tensors="pt")
input_ids = encodings["input_ids"]
attention_mask = encodings["attention_mask"]
labels = input_ids.clone()

print(f"Токенизировано: {input_ids.shape}")

# === Загрузка модели ===
print("Загрузка модели...")
model = AutoModelForCausalLM.from_pretrained(
    MODEL_PATH,
    torch_dtype=torch.bfloat16,
    device_map="auto",
    trust_remote_code=True,
)
model.train()
print(f"Модель загружена. VRAM: {torch.cuda.memory_allocated()/1e9:.2f} GB")

# === LoRA реализация ===
class LoRALinear(nn.Module):
    """Низкоранговая адаптация для nn.Linear"""
    def __init__(self, linear: nn.Linear, r=LORA_R, alpha=LORA_ALPHA, dropout=LORA_DROPOUT):
        super().__init__()
        self.linear = linear
        out_features, in_features = linear.weight.shape
        self.lora_A = nn.Parameter(torch.zeros(r, in_features, dtype=torch.bfloat16))
        self.lora_B = nn.Parameter(torch.zeros(out_features, r, dtype=torch.bfloat16))
        self.scaling = alpha / r
        self.dropout = nn.Dropout(dropout)
        nn.init.kaiming_uniform_(self.lora_A, a=math.sqrt(5))
        nn.init.zeros_(self.lora_B)

    def forward(self, x):
        result = self.linear(x)
        lora_out = self.dropout(x) @ self.lora_A.T @ self.lora_B.T
        return result + lora_out * self.scaling

# Замена целевых модулей на LoRA
target_modules = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]
lora_params = []
replaced = 0

def apply_lora(module, prefix=""):
    global replaced
    for name, child in module.named_children():
        full_name = f"{prefix}.{name}" if prefix else name
        if name in target_modules and isinstance(child, nn.Linear):
            lora_linear = LoRALinear(child)
            setattr(module, name, lora_linear)
            lora_params.extend([lora_linear.lora_A, lora_linear.lora_B])
            replaced += 1
        else:
            apply_lora(child, full_name)

apply_lora(model)
print(f"Заменено модулей: {replaced}")

# Заморозка базовых весов
for name, param in model.named_parameters():
    param.requires_grad = False
for param in lora_params:
    param.requires_grad = True

trainable = sum(p.numel() for p in lora_params)
total = sum(p.numel() for p in model.parameters())
print(f"Trainable: {trainable:,} / Total: {total:,} ({100*trainable/total:.2f}%)")

# === Обучение ===
optimizer = torch.optim.AdamW(lora_params, lr=LR)
num_batches = len(input_ids)
total_steps = (num_batches * EPOCHS) // (BATCH_SIZE * GRAD_ACCUM)

print(f"\n=== Начало обучения: {EPOCHS} эпох, {num_batches} примеров, {total_steps} шагов ===")

for epoch in range(EPOCHS):
    total_loss = 0
    optimizer.zero_grad()

    for i in range(0, num_batches, BATCH_SIZE):
        batch_ids = input_ids[i:i+BATCH_SIZE].to(device)
        batch_mask = attention_mask[i:i+BATCH_SIZE].to(device)
        batch_labels = labels[i:i+BATCH_SIZE].to(device)

        outputs = model(input_ids=batch_ids, attention_mask=batch_mask, labels=batch_labels)
        loss = outputs.loss / GRAD_ACCUM
        loss.backward()
        total_loss += loss.item()

        if (i // BATCH_SIZE + 1) % GRAD_ACCUM == 0 or i + BATCH_SIZE >= num_batches:
            torch.nn.utils.clip_grad_norm_(lora_params, 1.0)
            optimizer.step()
            optimizer.zero_grad()

    avg_loss = total_loss / (num_batches / GRAD_ACCUM)
    print(f"Эпоха {epoch+1}/{EPOCHS}: loss={avg_loss:.4f}")

# === Сохранение адаптера ===
print(f"\nСохранение в {OUTPUT_DIR}...")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Сохраняем только LoRA веса (lora_A, lora_B для каждого модуля)
lora_state = {}
for name, module in model.named_modules():
    if isinstance(module, LoRALinear):
        lora_state[f"{name}.lora_A"] = module.lora_A.data.clone()
        lora_state[f"{name}.lora_B"] = module.lora_B.data.clone()
        lora_state[f"{name}.scaling"] = module.scaling

torch.save(lora_state, os.path.join(OUTPUT_DIR, "adapter_model.pt"))

# Конфигурация
config = {
    "lora_rank": LORA_R,
    "lora_alpha": LORA_ALPHA,
    "lora_dropout": LORA_DROPOUT,
    "target_modules": target_modules,
    "base_model": "Qwen2.5-14B-Instruct",
    "base_model_path": MODEL_PATH,
    "dataset_size": len(examples),
    "epochs": EPOCHS,
    "modules_replaced": replaced,
}
with open(os.path.join(OUTPUT_DIR, "adapter_config.json"), "w") as f:
    json.dump(config, f, indent=2, ensure_ascii=False)

# Сохраняем токенизатор
tokenizer.save_pretrained(OUTPUT_DIR)

size_mb = sum(os.path.getsize(os.path.join(OUTPUT_DIR, f)) for f in os.listdir(OUTPUT_DIR)) / 1e6
print(f"=== ГОТОВО: {OUTPUT_DIR} ({size_mb:.1f} MB) ===")
